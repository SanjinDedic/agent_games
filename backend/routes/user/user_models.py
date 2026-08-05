from typing import Literal, Optional, Union

from pydantic import BaseModel, field_validator

# The server path streams stdout back without truncation, but a client-run
# result is attacker-controlled — bound what a tampered client can persist.
MAX_RESULT_STDOUT_CHARS = 50_000


class AgentResultSubmissionRequest(BaseModel):
    """A finished in-browser agent validation, submitted for storage.

    The browser is the only executor: the envelope comes either from the
    Pyodide run (frontend/src/pyodide/validation_harness.py) or, when Pyodide
    couldn't run, from the browser's direct call to the validation Lambda's
    Function URL — the latter tagged ``execution_source="pyodide_fallback"``
    with a ``fallback_reason``, counted in the shared telemetry. The
    client-reported results only feed the informational validation ranking
    (league standings come from separate league simulations), but the code
    itself is re-gated by the server-side AST check before storage — stored
    submissions are later executed in teachers' browsers by the league
    simulation runner. ``traceback`` is accepted only to feed the hint
    context on ``?generate_hint=true`` requests; it is never persisted.
    """

    code: str
    status: Literal["success", "error"]
    message: Optional[str] = None
    feedback: Optional[Union[str, dict]] = None
    simulation_results: Optional[dict] = None
    duration_ms: Optional[float] = None
    traceback: Optional[str] = None
    stdout: Optional[str] = None
    execution_source: Literal["pyodide", "pyodide_fallback"] = "pyodide"
    fallback_reason: Optional[str] = None

    @field_validator("stdout", "traceback")
    @classmethod
    def truncate_output(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return value[:MAX_RESULT_STDOUT_CHARS]

    @field_validator("fallback_reason")
    @classmethod
    def clean_fallback_reason(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()[:500]
        return value or None


class LeagueAssignRequest(BaseModel):
    """Model for assigning teams to leagues"""

    league_id: int


class GameName(BaseModel):
    """Model for specifying game names"""

    game_name: str

    @field_validator("game_name")
    def validate_game_name(cls, v):
        if not v.strip():
            raise ValueError("Game name must not be empty")
        return v.strip()


class DirectLeagueSignup(BaseModel):
    """Classic (non-curated) team signup: client-chosen team_name and free-text
    school_name. School-league signups (curated dropdown, server-assigned team
    name) use DirectSchoolLeagueSignup instead.
    """

    team_name: str
    password: str
    signup_token: str
    school_name: str = ""

    @field_validator("team_name", "password")
    def validate_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()


class TeamPasswordReset(BaseModel):
    """Consume a password-reset link: set a new password for its team."""

    reset_token: str
    password: str

    @field_validator("reset_token", "password")
    def validate_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()


class DirectSchoolLeagueSignup(BaseModel):
    """Model for direct team signup for a school league.

    Team name is server-generated from the selected school + counter — not
    supplied by the client. No email; password is the only credential.
    """

    signup_token: str
    school_name: str
    password: str

    @field_validator("signup_token", "school_name", "password")
    def validate_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()
