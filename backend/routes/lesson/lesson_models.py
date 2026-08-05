import re
from typing import Optional

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


class SnippetFallbackBeacon(BaseModel):
    """Telemetry ping for a snippet the browser ran via the direct Lambda
    Function URL (the server never executes snippet code) — keeps the
    pyodide-fallback counters honest."""

    reason: Optional[str] = None

    @field_validator("reason")
    @classmethod
    def clean_reason(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()[:500]
        return value or None
