"""Effective-access resolution via materialized paths.

A user may access a node iff an active, in-window grant exists on the node
itself or any ancestor: the node's path_ids starts with the granted node's
path_ids (every path_ids ends in the node's own id, so a file grant matches
exactly itself). One indexed LIKE — no recursive walk.
"""

from datetime import datetime, timezone

from sqlalchemy import func, literal, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DriveNode, Grant, User
from app.services.security import is_admin_email

_LIKE_ESCAPE = "\\"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _like_escaped(column):
    """SQL expression that neutralizes LIKE metacharacters (`\\`, `%`, `_`) in a
    column's value so it can be used as a literal prefix. Drive IDs contain `_`,
    which would otherwise act as a single-char wildcard and make the subtree
    access check match unrelated siblings (fail open)."""
    escaped = func.replace(column, _LIKE_ESCAPE, _LIKE_ESCAPE + _LIKE_ESCAPE)
    escaped = func.replace(escaped, "%", _LIKE_ESCAPE + "%")
    return func.replace(escaped, "_", _LIKE_ESCAPE + "_")


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
                literal(node.path_ids).like(
                    _like_escaped(DriveNode.path_ids) + "%", escape=_LIKE_ESCAPE
                ),
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
