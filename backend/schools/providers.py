import csv
import io
import logging
import re
from typing import List, Optional, Protocol

import httpx

from backend.database.db_models import League
from backend.schools.config import (
    GoogleSheetsSchoolsConfig,
    StaticSchoolsConfig,
    parse_schools_config,
)

logger = logging.getLogger(__name__)

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

    Sheet sharing must be set to 'Anyone with the link: Viewer'. The first
    row is treated as a header and skipped; column A supplies the values.
    """

    def __init__(self, sheet_url: str):
        self._url = sheet_url

    def list_schools(self) -> List[str]:
        csv_url = _to_csv_export_url(self._url)
        try:
            resp = httpx.get(csv_url, timeout=5.0, follow_redirects=True)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            logger.warning("Sheets fetch failed for %s: %s", csv_url, e)
            raise SchoolsProviderError(
                f"Could not fetch schools from sheet: {e}"
            )

        reader = csv.reader(io.StringIO(resp.text))
        rows = list(reader)
        return [
            row[0].strip() for row in rows[1:] if row and row[0].strip()
        ]


def get_schools_provider(league: League) -> Optional[SchoolsProvider]:
    if not league.school_league:
        return None
    try:
        cfg = parse_schools_config(league.schools_config or {})
    except Exception as e:
        raise SchoolsProviderError(f"Invalid schools_config: {e}")
    if isinstance(cfg, StaticSchoolsConfig):
        return StaticSchoolsProvider(cfg.schools)
    if isinstance(cfg, GoogleSheetsSchoolsConfig):
        return GoogleSheetsSchoolsProvider(cfg.sheet_url)
    raise SchoolsProviderError(f"Unknown schools source: {cfg!r}")
