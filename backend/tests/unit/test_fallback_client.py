"""Unit tests for the fallback client (backend/fallback_lambda/client.py).

Local mode runs the real subprocess pipeline — fresh interpreter, scrubbed
env, process-group kill — because that IS the dev/CI execution path and the
prod emergency fallback. Lambda mode mocks the boto3 boundary: the contract
under test is payload passthrough and the error→envelope mapping, never AWS
itself.
"""

import io
import json
from unittest.mock import MagicMock

import pytest
from botocore.config import Config
from botocore.exceptions import ClientError, ReadTimeoutError

from backend.fallback_lambda import client
from backend.fallback_lambda.client import (
    EXERCISE_LAMBDA_ENV,
    run_exercise_fallback,
    run_snippet_fallback,
    timeout_exercise_result,
)
from backend.fallback_lambda.executor import (
    EXERCISE_TIMEOUT_MESSAGE,
    SNIPPET_TIMEOUT_MESSAGE,
)

ADD_CODE = "def add(a, b):\n    return a + b"

ADD_TEST_CODE = (
    "def test_add():\n"
    '    """adds two numbers"""\n'
    "    check(add(1, 2), 3)\n"
)

EXERCISE_KEYS = {
    "status",
    "message",
    "passed",
    "test_results",
    "duration_ms",
    "traceback",
    "stdout",
}


def test_timeout_exercise_result_shape():
    result = timeout_exercise_result()
    assert result["status"] == "error"
    assert result["message"] == EXERCISE_TIMEOUT_MESSAGE
    assert result["passed"] is False
    assert result["test_results"] == []


# ---------------------------------------------------------------------------
# Local mode (EXERCISE_LAMBDA_FUNCTION unset): real subprocess execution.
# ---------------------------------------------------------------------------


@pytest.fixture
def local_mode(monkeypatch):
    monkeypatch.delenv(EXERCISE_LAMBDA_ENV, raising=False)


@pytest.mark.asyncio
async def test_local_passing_exercise(local_mode):
    result = await run_exercise_fallback(ADD_CODE, "add", ADD_TEST_CODE)
    assert set(result) == EXERCISE_KEYS
    assert result["status"] == "success"
    assert result["passed"] is True
    assert result["test_results"][0]["name"] == "adds two numbers"


@pytest.mark.asyncio
async def test_local_spinner_maps_to_timeout_envelope(local_mode):
    result = await run_exercise_fallback(
        "while True:\n    pass", "add", ADD_TEST_CODE
    )
    assert result["status"] == "error"
    assert result["message"] == EXERCISE_TIMEOUT_MESSAGE


@pytest.mark.asyncio
async def test_local_snippet_success(local_mode):
    result = await run_snippet_fallback("print('hello')")
    assert result["status"] == "success"
    assert result["stdout"] == "hello\n"


@pytest.mark.asyncio
async def test_local_snippet_spinner_maps_to_timeout_envelope(local_mode):
    result = await run_snippet_fallback("while True:\n    pass")
    assert result["status"] == "error"
    assert result["message"] == SNIPPET_TIMEOUT_MESSAGE


@pytest.mark.asyncio
async def test_local_env_is_scrubbed(local_mode, monkeypatch):
    # The subprocess must not inherit the API's environment: a canary set
    # here has to be invisible to student code (as SECRET_KEY/DATABASE_URL
    # must be in the real API process).
    monkeypatch.setenv("FALLBACK_CANARY_SECRET", "leaked")
    result = await run_snippet_fallback(
        "import os\nprint(os.environ.get('FALLBACK_CANARY_SECRET'))"
    )
    assert result["status"] == "success"
    assert result["stdout"] == "None\n"


@pytest.mark.asyncio
async def test_local_direct_fd1_write_cannot_corrupt_result(local_mode):
    # os.write(1, ...) bypasses sys.stdout redirection; local_run points fd 1
    # at /dev/null and reports on a private dup, so the envelope stays clean.
    result = await run_snippet_fallback(
        "import os\nos.write(1, b'garbage')\nprint('ok')"
    )
    assert result["status"] == "success"


@pytest.mark.asyncio
async def test_local_dead_runner_maps_to_timeout_envelope(
    local_mode, monkeypatch
):
    # A runner that dies without producing output (the OOM-kill shape) must
    # collapse to the timeout envelope, not raise.
    monkeypatch.setattr(client, "_run_local_sync", lambda event: None)
    result = await run_exercise_fallback(ADD_CODE, "add", ADD_TEST_CODE)
    assert result["status"] == "error"
    assert result["message"] == EXERCISE_TIMEOUT_MESSAGE


# ---------------------------------------------------------------------------
# Lambda mode (EXERCISE_LAMBDA_FUNCTION set): mocked boto3 boundary.
# ---------------------------------------------------------------------------


def _lambda_response(payload: dict, function_error: str = None):
    response = {"Payload": io.BytesIO(json.dumps(payload).encode())}
    if function_error:
        response["FunctionError"] = function_error
    return response


@pytest.fixture
def lambda_mode(monkeypatch):
    monkeypatch.setenv(EXERCISE_LAMBDA_ENV, "agent-games-exercise-fallback")
    mock_client = MagicMock()
    monkeypatch.setattr(client, "_lambda_client", mock_client)
    return mock_client


@pytest.mark.asyncio
async def test_lambda_success_passes_envelope_through(lambda_mode):
    envelope = {
        "status": "success",
        "message": None,
        "passed": True,
        "test_results": [{"name": "adds", "passed": True}],
        "duration_ms": 1.5,
        "traceback": None,
        "stdout": None,
    }
    lambda_mode.invoke.return_value = _lambda_response(envelope)

    result = await run_exercise_fallback(ADD_CODE, "add", ADD_TEST_CODE)
    assert result == envelope

    kwargs = lambda_mode.invoke.call_args.kwargs
    assert kwargs["FunctionName"] == "agent-games-exercise-fallback"
    event = json.loads(kwargs["Payload"])
    assert event == {
        "kind": "exercise",
        "code": ADD_CODE,
        "entry_function": "add",
        "test_code": ADD_TEST_CODE,
    }


@pytest.mark.asyncio
async def test_lambda_function_timeout_maps_to_timeout_envelope(lambda_mode):
    # The 3s function-timeout backstop fires when even the hard kill wedged;
    # same user-facing collapse as the old TimeLimitExceeded mapping.
    lambda_mode.invoke.return_value = _lambda_response(
        {"errorMessage": "2026-08-01T00:00:00Z Task timed out after 3.00 seconds"},
        function_error="Unhandled",
    )
    result = await run_exercise_fallback(ADD_CODE, "add", ADD_TEST_CODE)
    assert result["status"] == "error"
    assert result["message"] == EXERCISE_TIMEOUT_MESSAGE


@pytest.mark.asyncio
async def test_lambda_oom_maps_to_timeout_envelope(lambda_mode):
    lambda_mode.invoke.return_value = _lambda_response(
        {"errorMessage": "RequestId: abc Error: Runtime exited with error: signal: killed"},
        function_error="Unhandled",
    )
    result = await run_snippet_fallback("x = 'boom' * 10**9")
    assert result["status"] == "error"
    assert result["message"] == SNIPPET_TIMEOUT_MESSAGE


@pytest.mark.asyncio
async def test_lambda_read_timeout_maps_to_timeout_envelope(lambda_mode):
    lambda_mode.invoke.side_effect = ReadTimeoutError(
        endpoint_url="https://lambda.ap-southeast-2.amazonaws.com"
    )
    result = await run_exercise_fallback(ADD_CODE, "add", ADD_TEST_CODE)
    assert result["status"] == "error"
    assert result["message"] == EXERCISE_TIMEOUT_MESSAGE


@pytest.mark.asyncio
async def test_lambda_client_error_becomes_clean_error_envelope(lambda_mode):
    # Throttles, bad creds, missing function — service faults, not student
    # faults: a generic error envelope, never an exception to the route and
    # never AWS detail in the student-facing message.
    lambda_mode.invoke.side_effect = ClientError(
        {"Error": {"Code": "TooManyRequestsException", "Message": "throttled"}},
        "Invoke",
    )
    result = await run_exercise_fallback(ADD_CODE, "add", ADD_TEST_CODE)
    assert set(result) == EXERCISE_KEYS
    assert result["status"] == "error"
    assert "Error while running tests" in result["message"]
    assert "TooManyRequests" not in result["message"]


@pytest.mark.asyncio
async def test_lambda_handler_bug_becomes_clean_error_envelope(lambda_mode):
    lambda_mode.invoke.return_value = _lambda_response(
        {"errorMessage": "KeyError: 'entry_function'"},
        function_error="Unhandled",
    )
    result = await run_exercise_fallback(ADD_CODE, "add", ADD_TEST_CODE)
    assert result["status"] == "error"
    assert "Error while running tests" in result["message"]


def test_real_client_config_disables_retries(monkeypatch):
    # A retry would re-run student code; the read timeout must undercut the
    # router's patience (botocore defaults to 60s). Build the real client and
    # inspect its config.
    monkeypatch.setattr(client, "_lambda_client", None)
    built = client._get_lambda_client()
    config: Config = built.meta.config
    # botocore normalizes retries={"max_attempts": 0} to one total attempt.
    assert config.retries["total_max_attempts"] == 1
    assert config.read_timeout == client.INVOKE_READ_TIMEOUT
    assert config.connect_timeout == client.INVOKE_CONNECT_TIMEOUT
    monkeypatch.setattr(client, "_lambda_client", None)
