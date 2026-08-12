"""Add dx_sync_metrics table.

Revision ID: k1l2m3n4o5p6
Revises: j1k2l3m4n5o6
Create Date: 2026-08-12
"""

from alembic import op
import sqlalchemy as sa


revision = "k1l2m3n4o5p6"
down_revision = "j1k2l3m4n5o6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("dx_sync_metrics"):
        op.create_table(
            "dx_sync_metrics",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("document_id", sa.String(), nullable=True),
            sa.Column("event_type", sa.String(), nullable=False),
            sa.Column("status_code", sa.Integer(), nullable=False),
            sa.Column("error_kind", sa.String(), nullable=True),
            sa.Column("detail", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )
        op.create_index(
            "ix_dx_sync_metrics_event_type", "dx_sync_metrics", ["event_type"]
        )
        op.create_index(
            "ix_dx_sync_metrics_created_at", "dx_sync_metrics", ["created_at"]
        )


def downgrade() -> None:
    op.drop_index("ix_dx_sync_metrics_created_at", table_name="dx_sync_metrics")
    op.drop_index("ix_dx_sync_metrics_event_type", table_name="dx_sync_metrics")
    op.drop_table("dx_sync_metrics")
