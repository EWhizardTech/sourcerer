"""Catalog sync: upsert, move-repath, sweep, wikilink extraction."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.db.models import DriveNode, MdLink
from app.services import catalog_sync
from app.services.catalog_sync import sync_wikilinks, upsert_records
from app.services.gdrive import NodeRecord


def rec(
    node_id: str,
    parent_id: str | None,
    name: str,
    path_ids: str,
    path_names: str,
    depth: int,
    is_folder: bool = False,
    md5: str | None = None,
) -> NodeRecord:
    return NodeRecord(
        id=node_id,
        parent_id=parent_id,
        name=name,
        mime_type="application/vnd.google-apps.folder" if is_folder else "text/plain",
        is_folder=is_folder,
        size=None if is_folder else 5,
        modified_time="2026-08-01T00:00:00Z",
        md5_checksum=md5,
        path_ids=path_ids,
        path_names=path_names,
        depth=depth,
    )


def _tree_v1() -> list[NodeRecord]:
    return [
        rec("root", None, "Lib", "/root/", "Lib", 0, is_folder=True),
        rec("a", "root", "A", "/root/a/", "Lib/A", 1, is_folder=True),
        rec("f1", "a", "one.txt", "/root/a/f1/", "Lib/A/one.txt", 2, md5="h1"),
        rec("f2", "root", "two.txt", "/root/f2/", "Lib/two.txt", 1, md5="h2"),
    ]


async def test_upsert_inserts_all(db):
    now = datetime.now(timezone.utc)
    await upsert_records(db, _tree_v1(), now)
    ids = set((await db.execute(select(DriveNode.id))).scalars())
    assert ids == {"root", "a", "f1", "f2"}


async def test_move_rewrites_paths_and_keeps_id(db):
    now = datetime.now(timezone.utc)
    await upsert_records(db, _tree_v1(), now)

    moved = _tree_v1()
    moved[2] = rec("f1", "root", "one.txt", "/root/f1/", "Lib/one.txt", 1, md5="h1")
    await upsert_records(db, moved, now + timedelta(minutes=1))

    f1 = await db.get(DriveNode, "f1")
    assert f1.path_ids == "/root/f1/"
    assert f1.parent_id == "root"


async def test_sweep_deletes_removed_nodes(db):
    now = datetime.now(timezone.utc)
    await upsert_records(db, _tree_v1(), now)
    smaller = [r for r in _tree_v1() if r["id"] != "f2"]
    await upsert_records(db, smaller, now + timedelta(minutes=1))
    ids = set((await db.execute(select(DriveNode.id))).scalars())
    assert "f2" not in ids and "f1" in ids


async def test_upsert_reports_changed_md_only(db):
    now = datetime.now(timezone.utc)
    tree = _tree_v1() + [
        rec("m1", "root", "Note.md", "/root/m1/", "Lib/Note.md", 1, md5="v1")
    ]
    changed = await upsert_records(db, tree, now)
    assert changed == ["m1"]

    # Unchanged checksum -> not reported again; changed checksum -> reported.
    changed = await upsert_records(db, tree, now + timedelta(minutes=1))
    assert changed == []
    tree[-1] = rec("m1", "root", "Note.md", "/root/m1/", "Lib/Note.md", 1, md5="v2")
    changed = await upsert_records(db, tree, now + timedelta(minutes=2))
    assert changed == ["m1"]


async def test_wikilink_extraction_and_resolution(db, monkeypatch):
    now = datetime.now(timezone.utc)
    tree = _tree_v1() + [
        rec("m1", "root", "Index.md", "/root/m1/", "Lib/Index.md", 1, md5="v1"),
        rec("m2", "a", "Topic One.md", "/root/a/m2/", "Lib/A/Topic One.md", 2, md5="v1"),
    ]
    await upsert_records(db, tree, now)

    text = "See [[Topic One]] and [[Topic One#section]] and [[missing]] and [[one.txt]]"
    monkeypatch.setattr(
        catalog_sync, "download_file_bytes", lambda file_id: text.encode()
    )
    count = await sync_wikilinks(db, ["m1"])
    links = (await db.execute(select(MdLink))).scalars().all()
    targets = {link.target_id for link in links}
    assert count == 2
    assert targets == {"m2", "f1"}  # md link (deduped) + full-name file link
    assert all(link.source_id == "m1" for link in links)
