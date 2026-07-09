"""Single source of truth for time and timezone handling.

Policy:
- Every datetime in Python code and the database is timezone-aware UTC.
  Get "now" only via :func:`utc_now`; never call ``datetime.now()`` /
  ``datetime.utcnow()`` directly.
- Naive datetimes may still arrive from legacy rows or client payloads.
  Normalize them at the boundary with :func:`ensure_utc` (naive == UTC) or
  :func:`interpret_as_sydney` (naive == Sydney wall time, for user-typed dates).
- Australia/Sydney is a presentation concern only: convert with
  :func:`to_sydney` when rendering, never when storing or comparing.
"""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

UTC = timezone.utc
AUSTRALIA_SYDNEY_TZ = ZoneInfo("Australia/Sydney")


def utc_now() -> datetime:
    """Current time as an aware UTC datetime."""
    return datetime.now(UTC)


def ensure_utc(dt: datetime) -> datetime:
    """Normalize any datetime to aware UTC; naive input is assumed to be UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def interpret_as_sydney(dt: datetime) -> datetime:
    """Read a user-supplied datetime, treating naive values as Sydney wall time.

    Returns aware UTC either way.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=AUSTRALIA_SYDNEY_TZ)
    return dt.astimezone(UTC)


def to_sydney(dt: datetime) -> datetime:
    """Convert a stored datetime to Sydney time for display."""
    return ensure_utc(dt).astimezone(AUSTRALIA_SYDNEY_TZ)
