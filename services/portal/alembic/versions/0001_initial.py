"""Initial portal schema: users, catalog, requests, grants, audit.

Revision ID: 0001
Revises:
Create Date: 2026-08-16
"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

_request_status = sa.Enum(
    "pending", "approved", "denied", "cancelled",
    name="request_status", native_enum=False, length=16,
)
_grant_status = sa.Enum(
    "active", "revoked", name="grant_status", native_enum=False, length=16
)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("google_sub", sa.Text(), nullable=False, unique=True),
        sa.Column("email", sa.Text(), nullable=False, unique=True),
        sa.Column("name", sa.Text()),
        sa.Column("picture_url", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "drive_nodes",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "parent_id",
            sa.Text(),
            sa.ForeignKey("drive_nodes.id", ondelete="CASCADE"),
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.Text(), nullable=False),
        sa.Column("is_folder", sa.Boolean(), nullable=False),
        sa.Column("size", sa.BigInteger()),
        sa.Column("modified_time", sa.DateTime(timezone=True)),
        sa.Column("md5_checksum", sa.Text()),
        sa.Column("path_ids", sa.Text(), nullable=False),
        sa.Column("path_names", sa.Text(), nullable=False),
        sa.Column("depth", sa.Integer(), nullable=False),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_drive_nodes_parent_id", "drive_nodes", ["parent_id"])
    op.create_index(
        "ix_drive_nodes_path_ids",
        "drive_nodes",
        ["path_ids"],
        postgresql_ops={"path_ids": "text_pattern_ops"},
    )

    op.create_table(
        "md_links",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
                  primary_key=True, autoincrement=True),
        sa.Column(
            "source_id",
            sa.Text(),
            sa.ForeignKey("drive_nodes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "target_id",
            sa.Text(),
            sa.ForeignKey("drive_nodes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("link_text", sa.Text(), nullable=False),
        sa.UniqueConstraint("source_id", "target_id"),
    )
    op.create_index("ix_md_links_source_id", "md_links", ["source_id"])
    op.create_index("ix_md_links_target_id", "md_links", ["target_id"])

    op.create_table(
        "access_requests",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("message", sa.Text()),
        sa.Column("requested_days", sa.Integer(), nullable=False),
        sa.Column("status", _request_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        sa.Column("decided_by", sa.Uuid(), sa.ForeignKey("users.id")),
    )
    op.create_index("ix_access_requests_status", "access_requests", ["status"])

    op.create_table(
        "access_request_items",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
                  primary_key=True, autoincrement=True),
        sa.Column(
            "request_id",
            sa.Uuid(),
            sa.ForeignKey("access_requests.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "node_id", sa.Text(), sa.ForeignKey("drive_nodes.id"), nullable=False
        ),
        sa.UniqueConstraint("request_id", "node_id"),
    )
    op.create_index(
        "ix_access_request_items_request_id", "access_request_items", ["request_id"]
    )

    op.create_table(
        "grants",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "node_id", sa.Text(), sa.ForeignKey("drive_nodes.id"), nullable=False
        ),
        sa.Column("request_id", sa.Uuid(), sa.ForeignKey("access_requests.id")),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", _grant_status, nullable=False),
        sa.Column("granted_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
    )
    op.create_index(
        "ix_grants_user_status", "grants", ["user_id", "status", "expires_at"]
    )

    op.create_table(
        "audit_events",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
                  primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id")),
        sa.Column("event", sa.Text(), nullable=False),
        sa.Column("node_id", sa.Text()),
        sa.Column("meta", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_events_user_id", "audit_events", ["user_id"])
    op.create_index("ix_audit_events_created_at", "audit_events", ["created_at"])


def downgrade() -> None:
    for table in (
        "audit_events",
        "grants",
        "access_request_items",
        "access_requests",
        "md_links",
        "drive_nodes",
        "users",
    ):
        op.drop_table(table)
