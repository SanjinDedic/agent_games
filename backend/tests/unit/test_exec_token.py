"""Mint/verify parity for execution tokens.

The API mints with python-jose (auth_config.create_execution_token); the
Lambda verifies with the stdlib-only backend/fallback_lambda/exec_token.py.
These tests pin that pair together and pin the rejections that make the
verifier safe: wrong algorithm (including "none"), bad signature, expiry,
and missing scope.
"""

import base64
import hashlib
import hmac
import json
import time

import pytest

import backend.routes.auth.auth_config as auth_config
from backend.fallback_lambda import exec_token

SECRET = "unit-test-exec-secret"


@pytest.fixture(autouse=True)
def exec_secret(monkeypatch):
    monkeypatch.setattr(auth_config, "EXEC_JWT_SECRET", SECRET)


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def craft(claims: dict, secret: str = SECRET, alg: str = "HS256") -> str:
    """Hand-rolled token so tests can produce shapes jose refuses to mint."""
    header = _b64url(json.dumps({"alg": alg, "typ": "JWT"}).encode())
    payload = _b64url(json.dumps(claims).encode())
    signature = _b64url(
        hmac.new(
            secret.encode(), f"{header}.{payload}".encode(), hashlib.sha256
        ).digest()
    )
    return f"{header}.{payload}.{signature}"


def valid_claims(**overrides):
    claims = {
        "sub": "TeamA",
        "role": "student",
        "scope": "exec",
        "exp": int(time.time()) + 30,
    }
    claims.update(overrides)
    return claims


def test_jose_minted_token_verifies():
    token = auth_config.create_execution_token("TeamA", "student")
    claims = exec_token.verify(token, SECRET)
    assert claims is not None
    assert claims["sub"] == "TeamA"
    assert claims["role"] == "student"
    assert claims["scope"] == "exec"
    assert claims["exp"] > time.time()


def test_mint_without_secret_raises(monkeypatch):
    monkeypatch.setattr(auth_config, "EXEC_JWT_SECRET", None)
    with pytest.raises(RuntimeError):
        auth_config.create_execution_token("TeamA", "student")


def test_hand_crafted_token_verifies():
    """The smoke test in deploy.sh mints exactly this shape."""
    assert exec_token.verify(craft(valid_claims()), SECRET) is not None


def test_expired_token_rejected():
    token = craft(valid_claims(exp=int(time.time()) - 1))
    assert exec_token.verify(token, SECRET) is None


def test_far_future_exp_rejected():
    """A stolen EXEC_JWT_SECRET must not yield long-lived tokens: any exp
    beyond MAX_TTL_SECONDS is rejected even with a valid signature."""
    over_cap = int(time.time()) + exec_token.MAX_TTL_SECONDS + 5
    assert exec_token.verify(craft(valid_claims(exp=over_cap)), SECRET) is None
    year_out = int(time.time()) + 365 * 24 * 3600
    assert exec_token.verify(craft(valid_claims(exp=year_out)), SECRET) is None


def test_missing_or_wrong_scope_rejected():
    claims = valid_claims()
    del claims["scope"]
    assert exec_token.verify(craft(claims), SECRET) is None
    assert exec_token.verify(craft(valid_claims(scope="admin")), SECRET) is None


def test_wrong_secret_rejected():
    token = craft(valid_claims(), secret="some-other-secret")
    assert exec_token.verify(token, SECRET) is None


def test_alg_none_rejected():
    """A "none"-alg token must fail even with a valid-looking signature."""
    assert exec_token.verify(craft(valid_claims(), alg="none"), SECRET) is None
    # And with an empty signature segment, the classic attack shape.
    header = _b64url(json.dumps({"alg": "none", "typ": "JWT"}).encode())
    payload = _b64url(json.dumps(valid_claims()).encode())
    assert exec_token.verify(f"{header}.{payload}.", SECRET) is None


def test_non_hs256_alg_rejected():
    """Algorithm confusion: an RS256 header must be rejected before any
    signature interpretation, even though the HMAC bytes happen to match."""
    assert exec_token.verify(craft(valid_claims(), alg="RS256"), SECRET) is None


def test_garbage_tokens_rejected():
    for token in ("", "abc", "a.b", "a.b.c.d", "ä.ö.ü", None):
        assert exec_token.verify(token, SECRET) is None


def test_tampered_payload_rejected():
    token = craft(valid_claims())
    header, _, signature = token.split(".")
    forged = _b64url(json.dumps(valid_claims(sub="Mallory")).encode())
    assert exec_token.verify(f"{header}.{forged}.{signature}", SECRET) is None
