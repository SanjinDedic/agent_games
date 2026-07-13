from typing import List, Optional

from pydantic import BaseModel, field_validator


class ExerciseSubmissionRequest(BaseModel):
    """Model for exercise code submissions from teams"""

    exercise_id: int
    code: str


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
    (backend/tasks/exercise_test_code.py); `solution` is an optional
    reference solution for the admin editor. Both are stored as NULL when
    blank — for test_code so submitting hits the worker's loud "defines no
    tests" error instead of passing vacuously.
    """

    title: str
    problem_markdown: str
    starter_code: str = ""
    entry_function: str
    test_code: Optional[str] = None
    solution: Optional[str] = None

    @field_validator("test_code", "solution")
    @classmethod
    def blank_is_none(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and not value.strip():
            return None
        return value

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Exercise title cannot be empty")
        return value.strip()

    @field_validator("entry_function")
    @classmethod
    def entry_function_is_identifier(cls, value: str) -> str:
        value = value.strip()
        if not value.isidentifier():
            raise ValueError(
                "Entry function must be a valid Python function name"
            )
        return value


class ExerciseRunRequest(BaseModel):
    """Admin dry run: execute a test script against code without touching the
    DB. Stateless (no exercise id) so an exercise can be tested before it is
    ever saved."""

    code: str
    entry_function: str
    test_code: Optional[str] = None


class ExerciseReorderRequest(BaseModel):
    """The tutorial's complete exercise id list in the desired new order."""

    exercise_ids: List[int]
