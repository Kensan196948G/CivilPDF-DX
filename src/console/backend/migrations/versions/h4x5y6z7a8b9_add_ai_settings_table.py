"""add_ai_settings_table

Create the singleton ai_settings table (model: AiSetting). This table was
previously created only via Base.metadata.create_all and was missing from the
Alembic chain, so a fresh `alembic upgrade head` never created it.

Revision ID: h4x5y6z7a8b9
Revises: g3c4d5e6f7g8
Create Date: 2026-08-06 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "h4x5y6z7a8b9"
down_revision: Union[str, None] = "g3c4d5e6f7g8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("ai_settings"):
        return

    op.create_table(
        "ai_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("api_key_enc", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "model_name",
            sa.String(length=128),
            nullable=False,
            server_default="claude-haiku-4-5-20251001",
        ),
        sa.Column(
            "enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_by", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("id = 1", name="ck_ai_settings_singleton"),
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("ai_settings"):
        op.drop_table("ai_settings")
