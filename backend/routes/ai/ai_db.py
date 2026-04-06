import logging
from datetime import UTC, datetime
from typing import Dict, Optional

from sqlmodel import Session, select

from backend.database.db_models import AIProviderKey

logger = logging.getLogger(__name__)


def mask_key(key: Optional[str]) -> str:
    """Mask an API key for safe display. Shows first 4 and last 4 characters."""
    if not key:
        return ""
    if len(key) > 8:
        return f"{key[:4]}****{key[-4:]}"
    return "****"


def get_api_keys(session: Session) -> Dict:
    """Retrieve all AI provider keys, masked."""
    openai_row = session.exec(
        select(AIProviderKey).where(AIProviderKey.provider == "openai")
    ).first()
    return {
        "openai_api_key": mask_key(openai_row.api_key if openai_row else None),
    }


def update_api_key(session: Session, provider: str, api_key: str) -> None:
    """Upsert an AI provider key."""
    existing = session.exec(
        select(AIProviderKey).where(AIProviderKey.provider == provider)
    ).first()
    if existing:
        existing.api_key = api_key
        existing.updated_at = datetime.now(UTC)
        session.add(existing)
    else:
        new_key = AIProviderKey(
            provider=provider,
            api_key=api_key,
        )
        session.add(new_key)
    session.commit()


def get_stored_key(session: Session, provider: str) -> Optional[str]:
    """Get the raw (unmasked) key for a provider, or None."""
    row = session.exec(
        select(AIProviderKey).where(AIProviderKey.provider == provider)
    ).first()
    return row.api_key if row else None
