"""Effective-access resolution via materialized paths.

A user may access a node iff an active, in-window grant exists on the node
itself or any ancestor: the node's path_ids starts with the granted node's
path_ids (every path_ids ends in the node's own id, so a file grant matches
exactly itself). One indexed LIKE — no recursive walk.
"""

from datetime import datetime, timezone

from sqlalchemy import literal, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DriveNode, Grant, User
from app.services.security import is_admin_email


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def user_can_access(db: AsyncSession, user: User, node: DriveNode) -> bool:
    if is_admin_email(user.email):
        return True
    now = _now()
    hit = (
        await db.execute(
            select(Grant.id)
            .join(DriveNode, DriveNode.id == Grant.node_id)
            .where(
                Grant.user_id == user.id,
                Grant.status == "active",
                Grant.starts_at <= now,
                Grant.expires_at >= now,
                literal(node.path_ids).like(DriveNode.path_ids + "%"),
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    return hit is not None


async def active_grants(db: AsyncSession, user: User) -> list[tuple[Grant, DriveNode | None]]:
    """The user's active in-window grants, joined to their (possibly swept)
    catalog nodes — drives the 'unlocked' markers and the grants page."""
    now = _now()
    rows = (
        await db.execute(
            select(Grant, DriveNode)
            .outerjoin(DriveNode, DriveNode.id == Grant.node_id)
            .where(
                Grant.user_id == user.id,
                Grant.status == "active",
                Grant.starts_at <= now,
                Grant.expires_at >= now,
            )
            .order_by(Grant.expires_at)
        )
    ).all()
    return [(g, n) for g, n in rows]
