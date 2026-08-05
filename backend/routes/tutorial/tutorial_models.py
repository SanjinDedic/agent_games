from typing import List, Literal, Optional

from pydantic import BaseModel, field_validator

from backend.fallback_lambda.executor import MAX_STDOUT_CHARS


class ExerciseSubmissionRequest(BaseModel):
    """Model for exercise code submissions from teams.

    ``execution_source`` distinguishes the default server-run submission
    (wire value "celery", kept for contract stability after the Celery
    removal) from a browser submission that fell back to the server because
    Pyodide could not run (frontend/src/pyodide/exerciseRunnerClient.js).
    Fallbacks are logged and counted so the in-browser migration can prove
    when the fallback path has become dead weight.
    """

    exercise_id: int
    code: str
    execution_source: Literal["celery", "pyodide_fallback"] = "celery"
    fallback_reason: Optional[str] = None

    @field_validator("fallback_reason")
    @classmethod
    def clean_fallback_reason(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()[:500]
        return value or None


class ExerciseResultSubmissionRequest(BaseModel):
    """A finished in-browser (Pyodide) exercise run, submitted for storage.

    The browser already executed the code and the test script
    (frontend/src/pyodide/exercise_harness.py); this carries the normalized
    envelope so the attempt is recorded exactly like a worker-run one.
    Client results are trusted by design (exercises are practice, not
    assessment), but the server rebuilds each row from its contract keys and
    recomputes ``passed`` — see pyodide_support.normalize_client_rows.
    """

    exercise_id: int
    code: str
    status: Literal["success", "error"]
    message: Optional[str] = None
    passed: bool = False
    test_results: List[dict] = []
    stdout: Optional[str] = None
    duration_ms: Optional[float] = None
    # "pyodide" = the browser ran it locally (default). "pyodide_fallback" =
    # Pyodide couldn't run and the browser called the fallback Lambda's
    # Function URL directly — this envelope is that Lambda's result, and the
    # submission doubles as the fallback-telemetry beacon.
    execution_source: Literal["pyodide", "pyodide_fallback"] = "pyodide"
    fallback_reason: Optional[str] = None

    @field_validator("stdout")
    @classmethod
    def truncate_stdout(cls, value: Optional[str]) -> Optional[str]:
        # The harness truncates at the same bound; re-truncating here guards
        # against a tampered client bloating the stored payload.
        if value is None:
            return None
        return value[:MAX_STDOUT_CHARS]


class TutorialCreateRequest(BaseModel):
    title: str
    description: str = ""

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Tutorial title cannot be empty")
        return value.strip()


class TutorialUpdateRequest(BaseModel):
    title: str
    description: str

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Tutorial title cannot be empty")
        return value.strip()


class ExerciseRequest(BaseModel):
    """Full exercise definition, used for both create and update (PUT).

    `test_code` is the exercise's Python test script
    (backend/fallback_lambda/executor.py); `solution` is an optional
    reference solution for the admin editor. Both are stored as NULL when
    blank — for test_code so submitting hits the runner's loud "defines no
    tests" error instead of passing vacuously.
    """

    title: str
    problem_markdown: str
    starter_code: str = ""
    entry_function: str = ""
    test_code: Optional[str] = None
    solution: Optional[str] = None
    exercise_hints: List[str] = []

    @field_validator("test_code", "solution")
    @classmethod
    def blank_is_none(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and not value.strip():
            return None
        return value

    @field_validator("exercise_hints")
    @classmethod
    def drop_blank_hints(cls, value: List[str]) -> List[str]:
        return [hint.strip() for hint in value if hint.strip()]

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Exercise title cannot be empty")
        return value.strip()

    @field_validator("entry_function")
    @classmethod
    def entry_function_is_identifier(cls, value: str) -> str:
        # Empty means a top-level-code exercise: no function required, tests
        # grade module-level state and the worker-injected ``module_output``.
        value = value.strip()
        if value and not value.isidentifier():
            raise ValueError(
                "Entry function must be a valid Python function name"
            )
        return value


class ExerciseRunRequest(BaseModel):
    """Admin dry run: execute a test script against code without touching the
    DB. Stateless (no exercise id) so an exercise can be tested before it is
    ever saved."""

    code: str
    entry_function: str = ""
    test_code: Optional[str] = None


class ExerciseReorderRequest(BaseModel):
    """The tutorial's complete exercise id list in the desired new order."""

    exercise_ids: List[int]


class HintRevealRequest(BaseModel):
    """Which hint of an exercise a student just revealed (0-based index into
    Exercise.exercise_hints)."""

    hint_index: int

    @field_validator("hint_index")
    @classmethod
    def index_not_negative(cls, value: int) -> int:
        if value < 0:
            raise ValueError("hint_index cannot be negative")
        return value
