"""Add login lockout fields to users.

Revision ID: i1j2k3l4m5n6
Revises: h4x5y6z7a8b9
Create Date: 2026-08-12
"""

from alembic import op
import sqlalchemy as sa


revision = "i1j2k3l4m5n6"
down_revision = "h4x5y6z7a8b9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {c["name"] for c in inspector.get_columns("users")}
    if "failed_login_attempts" not in columns:
        op.add_column(
            "users",
            sa.Column(
                "failed_login_attempts",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
        )
    if "locked_until" not in columns:
        op.add_column(
            "users",
            sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {c["name"] for c in inspector.get_columns("users")}
    if "locked_until" in columns:
        op.drop_column("users", "locked_until")
    if "failed_login_attempts" in columns:
        op.drop_column("users", "failed_login_attempts")
