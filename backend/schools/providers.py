from typing import List, Optional, Protocol

from backend.database.db_models import League


class SchoolsProvider(Protocol):
    def list_schools(self) -> List[str]: ...


class StaticSchoolsProvider:
    def __init__(self, schools: List[str]):
        self._schools = [s.strip() for s in schools if s and s.strip()]

    def list_schools(self) -> List[str]:
        return list(self._schools)


class SchoolsProviderError(Exception):
    """Raised when a SchoolsProvider cannot be built from a League's schools_config."""


def get_schools_provider(league: League) -> Optional[SchoolsProvider]:
    if not league.school_league:
        return None
    cfg = league.schools_config or {}
    source = cfg.get("source", "static")
    if source == "static":
        return StaticSchoolsProvider(cfg.get("schools", []))
    raise SchoolsProviderError(f"Unknown schools source: {source}")
