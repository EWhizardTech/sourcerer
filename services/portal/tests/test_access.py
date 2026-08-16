"""Access-resolution semantics (materialized-path grant matching)."""

import uuid

from app.db.models import Grant
from app.services.access import user_can_access
from sourcerer_core.config import settings
from tests.conftest import make_node, make_user, utc


def _grant(user, node_id, *, start_days=-1, end_days=7, status="active", by=None):
    return Grant(
        id=uuid.uuid4(),
        user_id=user.id,
        node_id=node_id,
        starts_at=utc(start_days),
        expires_at=utc(end_days),
        status=status,
        granted_by=by or user.id,
        created_at=utc(),
    )


async def _seed(db):
    root = make_node("root", None, "Library", is_folder=True)
    sem5 = make_node("sem5", root, "Semester 05", is_folder=True)
    course = make_node("xw51", sem5, "20XW51", is_folder=True)
    file_in_course = make_node("f1", course, "notes.pdf")
    sibling = make_node("sem6", root, "Semester 06", is_folder=True)
    file_in_sibling = make_node("f2", sibling, "other.pdf")
    user = make_user()
    db.add_all([root, sem5, course, file_in_course, sibling, file_in_sibling, user])
    await db.commit()
    return user, file_in_course, file_in_sibling, sem5


async def test_direct_file_grant(db):
    user, file_node, *_ = await _seed(db)
    db.add(_grant(user, "f1"))
    await db.commit()
    assert await user_can_access(db, user, file_node)


async def test_ancestor_folder_grant_covers_descendants(db):
    user, file_node, _, sem5 = await _seed(db)
    db.add(_grant(user, "sem5"))
    await db.commit()
    assert await user_can_access(db, user, file_node)
    assert await user_can_access(db, user, sem5)


async def test_sibling_not_covered(db):
    user, _, sibling_file, _ = await _seed(db)
    db.add(_grant(user, "sem5"))
    await db.commit()
    assert not await user_can_access(db, user, sibling_file)


async def test_expired_grant_denied(db):
    user, file_node, *_ = await _seed(db)
    db.add(_grant(user, "f1", start_days=-10, end_days=-1))
    await db.commit()
    assert not await user_can_access(db, user, file_node)


async def test_not_yet_started_grant_denied(db):
    user, file_node, *_ = await _seed(db)
    db.add(_grant(user, "f1", start_days=1, end_days=10))
    await db.commit()
    assert not await user_can_access(db, user, file_node)


async def test_revoked_grant_denied(db):
    user, file_node, *_ = await _seed(db)
    db.add(_grant(user, "f1", status="revoked"))
    await db.commit()
    assert not await user_can_access(db, user, file_node)


async def test_no_grant_denied(db):
    user, file_node, *_ = await _seed(db)
    assert not await user_can_access(db, user, file_node)


async def test_admin_bypasses_grants(db, monkeypatch):
    user, file_node, *_ = await _seed(db)
    monkeypatch.setattr(settings, "ADMIN_EMAILS", user.email)
    assert await user_can_access(db, user, file_node)


async def test_grant_on_swept_node_matches_nothing(db):
    user, file_node, *_ = await _seed(db)
    db.add(_grant(user, "gone-node"))  # node no longer in the catalog
    await db.commit()
    assert not await user_can_access(db, user, file_node)


async def test_partial_id_prefix_is_not_a_match(db):
    """A grant on sem5 must not cover a sibling whose id starts with 'sem5' —
    the trailing slash in path_ids prevents prefix collisions."""
    from app.db.models import DriveNode

    user, *_ = await _seed(db)
    root = await db.get(DriveNode, "root")
    lookalike = make_node("sem5x", root, "Semester 05 Extra", is_folder=True)
    file_in_lookalike = make_node("f3", lookalike, "secret.pdf")
    db.add_all([lookalike, file_in_lookalike, _grant(user, "sem5")])
    await db.commit()
    assert not await user_can_access(db, user, file_in_lookalike)
