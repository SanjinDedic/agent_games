"""Function URL request handling in the fallback Lambda handler.

The direct browser path: a Function URL event carries an execution token and
a JSON body; the handler verifies the token (exec_token.py), caps sizes, and
wraps the ordinary envelope in an HTTP response. Execution is real — these
tests fork actual children through the executor, same as test_fallback_executor.
Plain invoke events (the API's boto3 path) must be completely unaffected.
"""

import base64
import hashlib
import hmac
import json
import time

import pytest

from backend.fallback_lambda import handler

SECRET = "http-test-exec-secret"

SNIPPET_KEYS = {"status", "message", "stdout", "traceback", "duration_ms"}
EXERCISE_KEYS = {
    "status", "message", "passed", "test_results",
    "duration_ms", "traceback", "stdout",
}


@pytest.fixture(autouse=True)
def exec_secret(monkeypatch):
    monkeypatch.setenv("EXEC_JWT_SECRET", SECRET)


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def make_token(secret: str = SECRET, **claim_overrides) -> str:
    claims = {"sub": "TeamA", "scope": "exec", "exp": int(time.time()) + 30}
    claims.update(claim_overrides)
    header = _b64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = _b64url(json.dumps(claims).encode())
    signature = _b64url(
        hmac.new(
            secret.encode(), f"{header}.{payload}".encode(), hashlib.sha256
        ).digest()
    )
    return f"{header}.{payload}.{signature}"


def make_event(payload, token=None, method="POST", base64_body=False):
    body = payload if isinstance(payload, str) else json.dumps(payload)
    if base64_body:
        body = base64.b64encode(body.encode()).decode()
    headers = {}
    if token is not None:
        headers["authorization"] = f"Bearer {token}"
    return {
        "requestContext": {"http": {"method": method, "path": "/"}},
        "headers": headers,
        "body": body,
        "isBase64Encoded": base64_body,
    }


def body_of(response):
    return json.loads(response["body"])


def test_snippet_runs_via_url():
    event = make_event({"kind": "snippet", "code": 'print("via url")'}, make_token())
    response = handler.lambda_handler(event, None)
    assert response["statusCode"] == 200
    envelope = body_of(response)
    assert set(envelope) == SNIPPET_KEYS
    assert envelope["status"] == "success"
    assert envelope["stdout"] == "via url\n"


def test_exercise_runs_via_url():
    event = make_event(
        {
            "kind": "exercise",
            "code": "def add(a, b):\n    return a + b\n",
            "entry_function": "add",
            "test_code": "def test_add():\n    check(add(1, 2), 3)\n",
        },
        make_token(),
    )
    response = handler.lambda_handler(event, None)
    assert response["statusCode"] == 200
    envelope = body_of(response)
    assert set(envelope) == EXERCISE_KEYS
    assert envelope["passed"] is True


def test_base64_body_is_decoded():
    event = make_event(
        {"kind": "snippet", "code": 'print("b64")'}, make_token(), base64_body=True
    )
    response = handler.lambda_handler(event, None)
    assert response["statusCode"] == 200
    assert body_of(response)["stdout"] == "b64\n"


@pytest.mark.parametrize(
    "token",
    [
        None,
        "not.a.token",
        make_token(secret="wrong-secret"),
        make_token(exp=int(time.time()) - 10),
        make_token(exp=int(time.time()) + 3600),
        make_token(scope="admin"),
    ],
)
def test_bad_tokens_are_401(token):
    event = make_event({"kind": "snippet", "code": "print(1)"}, token)
    response = handler.lambda_handler(event, None)
    assert response["statusCode"] == 401


def test_unset_secret_fails_closed(monkeypatch):
    """A misdeployed function (no EXEC_JWT_SECRET) must reject everything,
    never become an open code runner."""
    monkeypatch.delenv("EXEC_JWT_SECRET")
    event = make_event({"kind": "snippet", "code": "print(1)"}, make_token())
    response = handler.lambda_handler(event, None)
    assert response["statusCode"] == 401


def test_non_post_is_405():
    event = make_event({"kind": "snippet", "code": "print(1)"}, make_token(), method="GET")
    assert handler.lambda_handler(event, None)["statusCode"] == 405


@pytest.mark.parametrize(
    "payload",
    [
        "not json",
        json.dumps([1, 2, 3]),
        {"kind": "unknown", "code": "print(1)"},
        {"kind": "snippet", "code": 42},
        {"kind": "snippet"},
        {"kind": "exercise", "code": "x = 1", "entry_function": None},
        {"kind": "exercise", "code": "x = 1", "entry_function": "f", "test_code": {}},
    ],
)
def test_malformed_bodies_are_400(payload):
    event = make_event(payload, make_token())
    assert handler.lambda_handler(event, None)["statusCode"] == 400


def test_oversized_code_is_413():
    event = make_event(
        {"kind": "snippet", "code": "x" * (handler.MAX_CODE_CHARS + 1)},
        make_token(),
    )
    assert handler.lambda_handler(event, None)["statusCode"] == 413


def test_plain_invoke_events_are_untouched():
    """The API's boto3 path: no requestContext, no token, raw envelope out."""
    result = handler.lambda_handler(
        {"kind": "snippet", "code": 'print("plain")'}, None
    )
    assert set(result) == SNIPPET_KEYS
    assert result["stdout"] == "plain\n"
