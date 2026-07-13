from typing import List

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
    """Exercise definition, used for both create and update (PUT).

    Deliberately excludes `test_code`: the test script is seed-managed, so an
    admin editing title/markdown through this model can neither see nor
    clobber it.
    """

    title: str
    problem_markdown: str
    starter_code: str = ""
    entry_function: str

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


class ExerciseReorderRequest(BaseModel):
    """The tutorial's complete exercise id list in the desired new order."""

    exercise_ids: List[int]
