"""Append-only audit trail helper."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditEvent


async def record(
    db: AsyncSession,
    event: str,
    user_id: uuid.UUID | None = None,
    node_id: str | None = None,
    meta: dict | None = None,
) -> None:
    """Add an audit row to the session (committed with the caller's commit)."""
    db.add(AuditEvent(user_id=user_id, event=event, node_id=node_id, meta=meta))
