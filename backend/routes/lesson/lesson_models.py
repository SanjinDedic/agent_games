import re

from pydantic import BaseModel, field_validator

# Slugs appear verbatim in lesson:// links inside authored markdown, so keep
# them URL-safe and predictable: lowercase words separated by single hyphens.
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SLUG_MAX_LENGTH = 80


class LessonRequest(BaseModel):
    """Full lesson definition, used for both create and update (PUT)."""

    slug: str
    title: str
    content: str = ""

    @field_validator("slug")
    @classmethod
    def slug_is_valid(cls, value: str) -> str:
        value = value.strip()
        if not SLUG_RE.fullmatch(value):
            raise ValueError(
                "Slug must be lowercase words separated by hyphens "
                "(e.g. 'loops-basics')"
            )
        if len(value) > SLUG_MAX_LENGTH:
            raise ValueError(
                f"Slug cannot be longer than {SLUG_MAX_LENGTH} characters"
            )
        return value

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Lesson title cannot be empty")
        return value.strip()


class SnippetRunRequest(BaseModel):
    """Run one lesson code block: execute the code, return its output."""

    code: str

    @field_validator("code")
    @classmethod
    def code_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Code cannot be empty")
        return value
