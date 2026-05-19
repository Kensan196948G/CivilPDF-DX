"""add_m365_settings

Revision ID: a7e1d4f88c20
Revises: b669f56cdac7
Create Date: 2026-05-15 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a7e1d4f88c20"
down_revision: Union[str, Sequence[str], None] = "b669f56cdac7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema — create singleton m365_settings table."""
    op.create_table(
        "m365_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("client_id", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("client_secret_enc", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "auto_provision",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column(
            "default_role",
            sa.String(length=16),
            nullable=False,
            server_default="viewer",
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
        sa.CheckConstraint("id = 1", name="ck_m365_settings_singleton"),
    )


def downgrade() -> None:
    """Downgrade schema — drop m365_settings table."""
    op.drop_table("m365_settings")
