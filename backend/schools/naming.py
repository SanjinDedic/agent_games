"""School-name sanitization shared by the team-naming logic and the
LeagueSignUp validator. Lives in the neutral schools package so neither
``backend.routes.user`` nor ``backend.routes.institution`` has to import
across route boundaries.
"""

import re


def sanitize_school_name(s: str) -> str:
    """Strip all non-alphanumerics; preserve casing.

    'Willetton SHS!' -> 'WillettonSHS'. Accents/non-ASCII are stripped (e.g.
    'École' -> 'cole'); callers that need Unicode should pre-normalize.
    """
    return re.sub(r"[^A-Za-z0-9]", "", s or "")
