"""Failover across an ordered chain of (provider, model) attempts.

Any AIClientError — missing key, HTTP error, timeout, malformed response,
schema mismatch — moves to the next attempt. Success returns which
provider/model actually served, so callers can report it.
"""

import logging
from typing import List, Optional, Sequence, Tuple, Type

from sqlmodel import Session

from backend.routes.ai.clients.base import (
    AIClientError,
    LLMResponseError,
    NoApiKeyError,
    T,
)
from backend.routes.ai.clients.factory import get_ai_client

logger = logging.getLogger(__name__)


async def complete_structured_failover(
    session: Session,
    attempts: Sequence[Tuple[str, str]],
    *,
    system: str,
    user: str,
    schema: Type[T],
    temperature: Optional[float] = None,
    reasoning_effort: Optional[str] = None,
    max_tokens: Optional[int] = None,
) -> Tuple[T, str, str]:
    """Try each (provider, model) in order; return (result, provider, model) of the first success."""
    if not attempts:
        raise ValueError("attempts must contain at least one (provider, model) pair")

    failures: List[Tuple[str, str, AIClientError]] = []
    for provider, model in attempts:
        try:
            client = get_ai_client(session, provider)
            result = await client.complete_structured(
                system=system,
                user=user,
                schema=schema,
                model=model,
                temperature=temperature,
                reasoning_effort=reasoning_effort,
                max_tokens=max_tokens,
            )
        except AIClientError as e:
            logger.warning("AI failover: %s/%s failed: %s", provider, model, e)
            failures.append((provider, model, e))
            continue
        if failures:
            logger.info(
                "AI failover: served by %s/%s after %d failed attempt(s)",
                provider,
                model,
                len(failures),
            )
        return result, provider, model

    detail = "; ".join(f"{p}/{m}: {e}" for p, m, e in failures)
    if all(isinstance(e, NoApiKeyError) for _, _, e in failures):
        raise NoApiKeyError(f"No provider in the failover chain has an API key configured: {detail}")
    raise LLMResponseError(f"All AI providers failed: {detail}")
