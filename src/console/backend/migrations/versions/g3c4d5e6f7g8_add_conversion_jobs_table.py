"""add_conversion_jobs_table

Revision ID: g3c4d5e6f7g8
Revises: f2b3c4d5e6f7
Create Date: 2026-06-21 12:02:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "g3c4d5e6f7g8"
down_revision: Union[str, None] = "f2b3c4d5e6f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("conversion_jobs"):
        op.create_table(
            "conversion_jobs",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("document_id", sa.String(), nullable=False),
            sa.Column("job_type", sa.String(), nullable=False),
            sa.Column("status", sa.String(), nullable=True, server_default="pending"),
            sa.Column("output_path", sa.String(), nullable=True),
            sa.Column("output_size", sa.BigInteger(), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("requested_by", sa.String(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("(CURRENT_TIMESTAMP)"),
                nullable=True,
            ),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
            sa.ForeignKeyConstraint(["requested_by"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    if not inspector.has_index("conversion_jobs", "ix_conversion_jobs_document_id"):
        op.create_index(
            "ix_conversion_jobs_document_id",
            "conversion_jobs",
            ["document_id"],
        )
    if not inspector.has_index("conversion_jobs", "ix_conversion_jobs_status"):
        op.create_index(
            "ix_conversion_jobs_status",
            "conversion_jobs",
            ["status"],
        )


def downgrade() -> None:
    op.drop_index("ix_conversion_jobs_status", table_name="conversion_jobs")
    op.drop_index("ix_conversion_jobs_document_id", table_name="conversion_jobs")
    op.drop_table("conversion_jobs")
