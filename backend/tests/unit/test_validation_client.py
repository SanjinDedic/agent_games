"""Unit tests for the validation client (backend/validation_lambda/client.py).

Local mode runs the real subprocess pipeline — fresh interpreter, scrubbed
env, config stub, process-group kill — because that IS the dev/CI execution
path and the prod emergency fallback. Lambda mode mocks the boto3 boundary:
the contract under test is payload passthrough and the error→envelope
mapping, never AWS itself.
"""

import io
import json
from unittest.mock import MagicMock

import pytest
from botocore.config import Config
from botocore.exceptions import ClientError, ReadTimeoutError

from backend.validation_lambda import client
from backend.validation_lambda.client import (
    VALIDATION_LAMBDA_ENV,
    run_validation_fallback,
)
from backend.validation_lambda.executor import TIMEOUT_MESSAGE

VALID_CODE = (
    "from games.greedy_pig.player import Player\n"
    "class CustomPlayer(Player):\n"
    "    def make_decision(self, game_state):\n"
    "        return 'bank'\n"
)

VALIDATION_KEYS = {
    "status",
    "message",
    "feedback",
    "simulation_results",
    "duration_ms",
    "traceback",
    "stdout",
}


# ---------------------------------------------------------------------------
# Local mode (VALIDATION_LAMBDA_FUNCTION unset): real subprocess execution.
# ---------------------------------------------------------------------------


@pytest.fixture
def local_mode(monkeypatch):
    monkeypatch.delenv(VALIDATION_LAMBDA_ENV, raising=False)


@pytest.mark.asyncio
async def test_local_passing_validation(local_mode):
    result = await run_validation_fallback(VALID_CODE, "greedy_pig", "test_team")
    assert set(result) == VALIDATION_KEYS
    assert result["status"] == "success"
    assert "test_team" in result["simulation_results"]["total_points"]


@pytest.mark.asyncio
async def test_local_spinner_kill_maps_to_timeout_envelope(
    local_mode, monkeypatch
):
    # The in-child SIGALRM path is covered fast in the executor tests; here
    # the client's own kill-and-collapse is under test, so shrink its
    # patience below the child's 5s soft limit instead of waiting it out.
    monkeypatch.setattr(client, "LOCAL_RUN_TIMEOUT", 1)
    spinner = (
        "from games.greedy_pig.player import Player\n"
        "class CustomPlayer(Player):\n"
        "    def make_decision(self, game_state):\n"
        "        while True:\n"
        "            pass\n"
    )
    result = await run_validation_fallback(spinner, "greedy_pig", "spin_team")
    assert result["status"] == "error"
    assert result["message"] == TIMEOUT_MESSAGE


@pytest.mark.asyncio
async def test_local_env_is_scrubbed(local_mode, monkeypatch):
    # The subprocess must not inherit the API's environment: a canary set
    # here has to be invisible to agent code (as SECRET_KEY/DATABASE_URL
    # must be in the real API process).
    monkeypatch.setenv("FALLBACK_CANARY_SECRET", "leaked")
    peeking = (
        "import os\n"
        "print('CANARY=' + repr(os.environ.get('FALLBACK_CANARY_SECRET')))\n"
        "from games.greedy_pig.player import Player\n"
        "class CustomPlayer(Player):\n"
        "    def make_decision(self, game_state):\n"
        "        return 'bank'\n"
    )
    result = await run_validation_fallback(peeking, "greedy_pig", "peek_team")
    assert result["status"] == "success"
    assert "CANARY=None" in result["stdout"]


@pytest.mark.asyncio
async def test_local_dotenv_is_not_reinjected(local_mode):
    # backend/config.py load_dotenv()s .env at import time; local_run installs
    # a config stub precisely so the games import cannot drag those secrets
    # into the environment of the process running agent code. SECRET_KEY is a
    # committed .env key, so it must be absent here.
    peeking = (
        "import os\n"
        "print('DOTENV=' + repr(os.environ.get('SECRET_KEY')))\n"
        "from games.greedy_pig.player import Player\n"
        "class CustomPlayer(Player):\n"
        "    def make_decision(self, game_state):\n"
        "        return 'bank'\n"
    )
    result = await run_validation_fallback(peeking, "greedy_pig", "peek_team")
    assert result["status"] == "success"
    assert "DOTENV=None" in result["stdout"]


@pytest.mark.asyncio
async def test_local_direct_fd1_write_cannot_corrupt_result(local_mode):
    # os.write(1, ...) bypasses sys.stdout redirection; local_run points fd 1
    # at /dev/null and reports on a private dup, so the envelope stays clean.
    writing = (
        "import os\n"
        "os.write(1, b'garbage')\n"
        "from games.greedy_pig.player import Player\n"
        "class CustomPlayer(Player):\n"
        "    def make_decision(self, game_state):\n"
        "        return 'bank'\n"
    )
    result = await run_validation_fallback(writing, "greedy_pig", "fd_team")
    assert result["status"] == "success"


@pytest.mark.asyncio
async def test_local_dead_runner_maps_to_timeout_envelope(
    local_mode, monkeypatch
):
    # A runner that dies without producing output (the OOM-kill shape) must
    # collapse to the timeout envelope, not raise.
    monkeypatch.setattr(client, "_run_local_sync", lambda event: None)
    result = await run_validation_fallback(VALID_CODE, "greedy_pig", "team")
    assert result["status"] == "error"
    assert result["message"] == TIMEOUT_MESSAGE


# ---------------------------------------------------------------------------
# Lambda mode (VALIDATION_LAMBDA_FUNCTION set): mocked boto3 boundary.
# ---------------------------------------------------------------------------


def _lambda_response(payload: dict, function_error: str = None):
    response = {"Payload": io.BytesIO(json.dumps(payload).encode())}
    if function_error:
        response["FunctionError"] = function_error
    return response


@pytest.fixture
def lambda_mode(monkeypatch):
    monkeypatch.setenv(VALIDATION_LAMBDA_ENV, "agent-games-validation")
    mock_client = MagicMock()
    monkeypatch.setattr(client, "_lambda_client", mock_client)
    return mock_client


@pytest.mark.asyncio
async def test_lambda_success_passes_envelope_through(lambda_mode):
    envelope = {
        "status": "success",
        "message": None,
        "feedback": "well played",
        "simulation_results": {"total_points": {"team": 1.0}},
        "duration_ms": 250.0,
        "traceback": None,
        "stdout": None,
    }
    lambda_mode.invoke.return_value = _lambda_response(envelope)

    result = await run_validation_fallback(VALID_CODE, "greedy_pig", "team")
    assert result == envelope

    kwargs = lambda_mode.invoke.call_args.kwargs
    assert kwargs["FunctionName"] == "agent-games-validation"
    event = json.loads(kwargs["Payload"])
    assert event == {
        "kind": "validation",
        "code": VALID_CODE,
        "game_name": "greedy_pig",
        "team_name": "team",
    }


@pytest.mark.asyncio
async def test_lambda_function_timeout_maps_to_timeout_envelope(lambda_mode):
    # The 8s function-timeout backstop fires when even the hard kill wedged;
    # same user-facing collapse as the old TimeLimitExceeded mapping.
    lambda_mode.invoke.return_value = _lambda_response(
        {"errorMessage": "2026-08-01T00:00:00Z Task timed out after 8.00 seconds"},
        function_error="Unhandled",
    )
    result = await run_validation_fallback(VALID_CODE, "greedy_pig", "team")
    assert result["status"] == "error"
    assert result["message"] == TIMEOUT_MESSAGE


@pytest.mark.asyncio
async def test_lambda_oom_maps_to_timeout_envelope(lambda_mode):
    # The 1769MB memory cap is the memory-bomb containment now (the old
    # worker relied on the container cgroup + WorkerLostError).
    lambda_mode.invoke.return_value = _lambda_response(
        {"errorMessage": "RequestId: abc Error: Runtime exited with error: signal: killed"},
        function_error="Unhandled",
    )
    result = await run_validation_fallback(VALID_CODE, "greedy_pig", "team")
    assert result["status"] == "error"
    assert result["message"] == TIMEOUT_MESSAGE


@pytest.mark.asyncio
async def test_lambda_read_timeout_maps_to_timeout_envelope(lambda_mode):
    lambda_mode.invoke.side_effect = ReadTimeoutError(
        endpoint_url="https://lambda.ap-southeast-2.amazonaws.com"
    )
    result = await run_validation_fallback(VALID_CODE, "greedy_pig", "team")
    assert result["status"] == "error"
    assert result["message"] == TIMEOUT_MESSAGE


@pytest.mark.asyncio
async def test_lambda_client_error_becomes_clean_error_envelope(lambda_mode):
    # Throttles, bad creds, missing function — service faults, not student
    # faults: a generic error envelope, never an exception to the route and
    # never AWS detail in the student-facing message.
    lambda_mode.invoke.side_effect = ClientError(
        {"Error": {"Code": "TooManyRequestsException", "Message": "throttled"}},
        "Invoke",
    )
    result = await run_validation_fallback(VALID_CODE, "greedy_pig", "team")
    assert set(result) == VALIDATION_KEYS
    assert result["status"] == "error"
    assert "Error during validation" in result["message"]
    assert "TooManyRequests" not in result["message"]


@pytest.mark.asyncio
async def test_lambda_handler_bug_becomes_clean_error_envelope(lambda_mode):
    lambda_mode.invoke.return_value = _lambda_response(
        {"errorMessage": "KeyError: 'game_name'"},
        function_error="Unhandled",
    )
    result = await run_validation_fallback(VALID_CODE, "greedy_pig", "team")
    assert result["status"] == "error"
    assert "Error during validation" in result["message"]


def test_real_client_config_disables_retries(monkeypatch):
    # A retry would re-run agent code; the read timeout must undercut the
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
