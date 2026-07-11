from typing import Any, List

from pydantic import BaseModel, field_validator


class ExerciseSubmissionRequest(BaseModel):
    """Model for exercise code submissions from teams"""

    exercise_id: int
    code: str


class TestCase(BaseModel):
    """One function I/O pair: the worker calls the entry function with `args`
    and compares the return value to `expected` with ==."""

    name: str
    args: List[Any]
    expected: Any

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Test case name cannot be empty")
        return value


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
    """Full exercise definition, used for both create and update (PUT)."""

    title: str
    problem_markdown: str
    starter_code: str = ""
    entry_function: str
    test_cases: List[TestCase]

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

    @field_validator("test_cases")
    @classmethod
    def at_least_one_test_case(cls, value: List[TestCase]) -> List[TestCase]:
        if not value:
            raise ValueError("An exercise needs at least one test case")
        return value


class ExerciseReorderRequest(BaseModel):
    """The tutorial's complete exercise id list in the desired new order."""

    exercise_ids: List[int]
