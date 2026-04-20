import csv
import io
import logging
import re
import time
from typing import Dict, List, Optional, Protocol, Tuple

import httpx

from backend.database.db_models import League

logger = logging.getLogger(__name__)

_DEFAULT_TTL_SECONDS = 300
_SHEET_CACHE: Dict[str, Tuple[float, List[str]]] = {}
_SHEET_ID_RE = re.compile(r"/spreadsheets/d/([a-zA-Z0-9_-]+)")
_GID_RE = re.compile(r"[#&?]gid=(\d+)")


class SchoolsProvider(Protocol):
    def list_schools(self) -> List[str]: ...


class SchoolsProviderError(Exception):
    """Raised when a SchoolsProvider cannot be built or cannot fetch its list."""


class StaticSchoolsProvider:
    def __init__(self, schools: List[str]):
        self._schools = [s.strip() for s in schools if s and s.strip()]

    def list_schools(self) -> List[str]:
        return list(self._schools)


def _to_csv_export_url(sheet_url: str) -> str:
    """Translate any Google Sheets URL into the CSV export URL for its gid (or gid=0)."""
    m = _SHEET_ID_RE.search(sheet_url)
    if not m:
        raise SchoolsProviderError(
            f"Not a recognisable Google Sheets URL: {sheet_url}"
        )
    sheet_id = m.group(1)
    gid_match = _GID_RE.search(sheet_url)
    gid = gid_match.group(1) if gid_match else "0"
    return (
        f"https://docs.google.com/spreadsheets/d/{sheet_id}"
        f"/export?format=csv&gid={gid}"
    )


class GoogleSheetsSchoolsProvider:
    """Fetches a public Google Sheet's first column as the list of schools.

    Sheet sharing must be set to 'Anyone with the link: Viewer'. The first row is
    treated as a header and skipped; column A supplies the values. Results are
    cached per URL with a 5-minute TTL; on fetch failure with a warm cache, the
    last-known-good list is served rather than breaking in-progress signups.
    """

    def __init__(self, sheet_url: str, ttl_seconds: int = _DEFAULT_TTL_SECONDS):
        self._url = sheet_url
        self._ttl = ttl_seconds

    def list_schools(self) -> List[str]:
        csv_url = _to_csv_export_url(self._url)
        now = time.monotonic()
        cached = _SHEET_CACHE.get(csv_url)
        if cached and now - cached[0] < self._ttl:
            return list(cached[1])

        try:
            resp = httpx.get(csv_url, timeout=5.0, follow_redirects=True)
            resp.raise_for_status()
        except Exception as e:
            logger.warning("Sheets fetch failed for %s: %s", csv_url, e)
            if cached:
                return list(cached[1])
            raise SchoolsProviderError(
                f"Could not fetch schools from sheet: {e}"
            )

        reader = csv.reader(io.StringIO(resp.text))
        rows = list(reader)
        schools = [
            row[0].strip() for row in rows[1:] if row and row[0].strip()
        ]
        _SHEET_CACHE[csv_url] = (now, schools)
        return schools


def get_schools_provider(league: League) -> Optional[SchoolsProvider]:
    if not league.school_league:
        return None
    cfg = league.schools_config or {}
    source = cfg.get("source", "static")
    if source == "static":
        return StaticSchoolsProvider(cfg.get("schools", []))
    if source == "google_sheets":
        return GoogleSheetsSchoolsProvider(cfg["sheet_url"])
    raise SchoolsProviderError(f"Unknown schools source: {source}")
