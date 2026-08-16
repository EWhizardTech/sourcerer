"""Shared fixtures: in-memory SQLite database (schema from ORM metadata)."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.models import DriveNode, User


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


def utc(days: int = 0) -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=days)


def make_user(email: str = "student@example.com") -> User:
    return User(
        id=uuid.uuid4(),
        google_sub=uuid.uuid4().hex,
        email=email,
        created_at=utc(),
    )


def make_node(
    node_id: str,
    parent: DriveNode | None,
    name: str,
    is_folder: bool = False,
    md5: str | None = None,
) -> DriveNode:
    path_ids = f"{parent.path_ids}{node_id}/" if parent else f"/{node_id}/"
    path_names = f"{parent.path_names}/{name}" if parent else name
    return DriveNode(
        id=node_id,
        parent_id=parent.id if parent else None,
        name=name,
        mime_type="application/vnd.google-apps.folder" if is_folder else "text/plain",
        is_folder=is_folder,
        size=None if is_folder else 10,
        modified_time=utc(),
        md5_checksum=md5,
        path_ids=path_ids,
        path_names=path_names,
        depth=parent.depth + 1 if parent else 0,
        synced_at=utc(),
    )
