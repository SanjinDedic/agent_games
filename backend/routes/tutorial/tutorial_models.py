from pydantic import BaseModel


class ExerciseSubmissionRequest(BaseModel):
    """Model for exercise code submissions from teams"""

    exercise_id: int
    code: str
