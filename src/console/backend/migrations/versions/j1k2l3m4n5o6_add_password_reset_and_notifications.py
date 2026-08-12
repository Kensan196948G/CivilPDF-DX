"""Add password reset fields and notifications table.

Revision ID: j1k2l3m4n5o6
Revises: i1j2k3l4m5n6
Create Date: 2026-08-12
"""

from alembic import op
import sqlalchemy as sa


revision = "j1k2l3m4n5o6"
down_revision = "i1j2k3l4m5n6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    user_columns = {c["name"] for c in inspector.get_columns("users")}
    if "password_reset_token_hash" not in user_columns:
        op.add_column(
            "users",
            sa.Column("password_reset_token_hash", sa.String(), nullable=True),
        )
    if "password_reset_expires_at" not in user_columns:
        op.add_column(
            "users",
            sa.Column(
                "password_reset_expires_at",
                sa.DateTime(timezone=True),
                nullable=True,
            ),
        )
    if not inspector.has_table("notifications"):
        op.create_table(
            "notifications",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("user_id", sa.String(), nullable=False),
            sa.Column("notification_type", sa.String(), nullable=False),
            sa.Column("title", sa.String(), nullable=False),
            sa.Column("body", sa.Text(), nullable=True),
            sa.Column("resource_type", sa.String(), nullable=True),
            sa.Column("resource_id", sa.String(), nullable=True),
            sa.Column("is_read", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("(CURRENT_TIMESTAMP)"),
                nullable=True,
            ),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
        op.create_index("ix_notifications_created_at", "notifications", ["created_at"])
    if bind.dialect.name == "postgresql":
        op.execute(
            "ALTER TABLE documents ADD COLUMN IF NOT EXISTS search_vector tsvector"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_documents_search_vector "
            "ON documents USING GIN (search_vector)"
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("notifications"):
        op.drop_table("notifications")
    user_columns = {c["name"] for c in inspector.get_columns("users")}
    if "password_reset_expires_at" in user_columns:
        op.drop_column("users", "password_reset_expires_at")
    if "password_reset_token_hash" in user_columns:
        op.drop_column("users", "password_reset_token_hash")
