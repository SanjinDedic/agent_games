"""Stdlib-only verifier for execution tokens (direct client→Lambda calls).

The API mints these with python-jose (``create_execution_token`` in
backend/routes/auth/auth_config.py) using a DEDICATED secret
(``EXEC_JWT_SECRET``) that is never the server's ``SECRET_KEY``: student code
runs in this process's forked children and can read process memory, so the
only secret allowed here is one whose theft grants nothing beyond invoking
this same sandbox. ``test_exec_token.py`` pins mint/verify parity.

Stdlib-only is a hard constraint (the deploy zip ships no dependencies), so
verification is done by hand: HS256 only — any other ``alg`` (including
``none`` and the RS-family confusion attacks) is rejected before the
signature check.
"""

import base64
import hashlib
import hmac
import json
import time
from typing import Any, Dict, Optional

REQUIRED_SCOPE = "exec"

# Reject tokens minted with an exp further out than this. The API mints
# 10-second tokens (auth_config.EXEC_TOKEN_EXPIRY_SECONDS); the generous gap
# absorbs clock skew between the API host and Lambda. The point: student code
# can read EXEC_JWT_SECRET from this process's memory and mint its own
# tokens, so legit-mint TTL alone bounds nothing — this cap is what keeps any
# token, stolen or self-minted, short-lived.
MAX_TTL_SECONDS = 60


def _b64url_decode(segment: str) -> bytes:
    return base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4))


def verify(token: str, secret: str) -> Optional[Dict[str, Any]]:
    """Return the claims dict for a valid token, None for anything else.

    Valid means: three well-formed segments, header ``alg`` exactly HS256,
    HMAC-SHA256 signature over ``header.payload`` matches (compare_digest),
    ``scope`` claim is ``exec``, and ``exp`` is in the future. Never raises.
    """
    if not token or not secret:
        return None
    parts = token.split(".")
    if len(parts) != 3:
        return None
    header_b64, payload_b64, signature_b64 = parts
    try:
        header = json.loads(_b64url_decode(header_b64))
        if not isinstance(header, dict) or header.get("alg") != "HS256":
            return None
        expected = hmac.new(
            secret.encode(),
            f"{header_b64}.{payload_b64}".encode(),
            hashlib.sha256,
        ).digest()
        if not hmac.compare_digest(expected, _b64url_decode(signature_b64)):
            return None
        claims = json.loads(_b64url_decode(payload_b64))
    except (ValueError, TypeError):
        return None
    if not isinstance(claims, dict):
        return None
    if claims.get("scope") != REQUIRED_SCOPE:
        return None
    exp = claims.get("exp")
    if not isinstance(exp, (int, float)):
        return None
    now = time.time()
    if exp <= now or exp > now + MAX_TTL_SECONDS:
        return None
    return claims
