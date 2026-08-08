"""Domain exceptions and their HTTP status codes.

Every exception a route may let propagate lives here, together with the single
map from class to status code that ``backend/api.py`` walks to register its
handlers. Defining them in one place is what lets ``LeagueNotFoundError`` mean
one thing: the league and team lookup errors used to be declared separately in
``institution_db`` and ``user_db``, imported into ``api.py`` under aliases, and
given one hand-written handler each.

Raising code imports from here. To add an exception, define it below and add a
row to ``EXCEPTION_STATUS_MAP`` — no handler to write.

This module imports nothing from ``backend.routes`` and must stay that way. The
route packages' ``__init__.py`` files eagerly import their routers, so a single
import back into ``backend.routes`` here closes a cycle: ``api`` -> ``errors``
-> some route package -> its router -> a ``*_db`` module -> ``errors``, which is
still half-initialized. That is why the AI provider and plagiarism exceptions
are defined here rather than in their own packages — those packages import them
back out and re-export them, so their public contracts are unchanged.
"""


# --- auth ------------------------------------------------------------------


class InvalidCredentialsError(Exception):
    """Raised when login credentials are invalid (maps to HTTP 401)."""


class AdminExistsError(Exception):
    """Raised when setup runs on a deployment that already has an admin
    (maps to HTTP 409)."""


# --- league ----------------------------------------------------------------


class LeagueNotFoundError(Exception):
    """Raised when a league does not exist or is not visible to the caller (maps to HTTP 404)."""


class LeagueExistsError(Exception):
    """Raised when attempting to create a league that already exists (maps to HTTP 409)."""


class LeagueExpiredError(Exception):
    """Raised when a signup targets a league past its expiry (maps to HTTP 410)."""


class ProtectedLeagueError(Exception):
    """Raised when an operation targets a league that may not be modified,
    e.g. deleting the auto-created 'unassigned' league (maps to HTTP 400)."""


class SchoolsConfigError(Exception):
    """Raised when a school league's schools_config is invalid or unreachable (maps to HTTP 400)."""


# --- team ------------------------------------------------------------------


class TeamError(Exception):
    """Base exception for all team-related errors."""


class TeamNotFoundError(TeamError):
    """Raised when the target team does not exist (maps to HTTP 404)."""


class TeamExistsError(TeamError):
    """Raised when a team name collides with an existing one (maps to HTTP 409)."""


class AgentTeamError(ValueError):
    """Raised for invalid agent-team / API-key operations (maps to HTTP 400).

    Subclasses ValueError so existing callers/tests that catch ValueError keep working.
    """


# --- submissions and results ----------------------------------------------


class SubmissionLimitExceededError(Exception):
    """Raised when the submission rate limit is exceeded (maps to HTTP 429)."""


class SimulationLimitExceededError(Exception):
    """Raised when the simulation rate limit is exceeded (maps to HTTP 429)."""


class SimulationResultNotFoundError(Exception):
    """Raised when a referenced simulation result does not exist (maps to HTTP 404)."""


class ResultNotFoundError(Exception):
    """Raised when a published result is not found (maps to HTTP 404)."""


# --- AI providers ----------------------------------------------------------
# Re-exported by backend/routes/ai/clients/base.py, which owns the provider
# contract; defined here so this module imports nothing from backend.routes.


class AIClientError(Exception):
    """Base error for AI client failures."""


class NoApiKeyError(AIClientError):
    """No API key is configured for the requested provider (maps to HTTP 400)."""


class UnknownProviderError(AIClientError):
    """The requested provider has no registered client (maps to HTTP 400)."""


class LLMResponseError(AIClientError):
    """The provider returned an unusable response — HTTP error, bad JSON, schema
    mismatch (maps to HTTP 502)."""


class AIRequestTimeoutError(AIClientError):
    """The provider did not respond within the request timeout (maps to HTTP 504)."""


# --- plagiarism ------------------------------------------------------------


class PlagiarismServiceError(Exception):
    """Base error for plagiarism service failures."""


class NoSubmissionsError(PlagiarismServiceError):
    """The team has no submissions to analyze (maps to HTTP 400)."""


class PayloadTooLargeError(PlagiarismServiceError):
    """Combined submission code exceeds the size limit (maps to HTTP 413)."""


# --- the map ---------------------------------------------------------------

# Order matters only for readability: FastAPI dispatches on the most specific
# registered class, so listing a base class alongside its subclasses is safe.
EXCEPTION_STATUS_MAP: dict[type[Exception], int] = {
    InvalidCredentialsError: 401,
    AdminExistsError: 409,
    LeagueNotFoundError: 404,
    LeagueExistsError: 409,
    LeagueExpiredError: 410,
    ProtectedLeagueError: 400,
    SchoolsConfigError: 400,
    TeamNotFoundError: 404,
    TeamExistsError: 409,
    AgentTeamError: 400,
    SubmissionLimitExceededError: 429,
    SimulationLimitExceededError: 429,
    SimulationResultNotFoundError: 404,
    ResultNotFoundError: 404,
    UnknownProviderError: 400,
    NoApiKeyError: 400,
    NoSubmissionsError: 400,
    PayloadTooLargeError: 413,
    LLMResponseError: 502,
    AIRequestTimeoutError: 504,
}
