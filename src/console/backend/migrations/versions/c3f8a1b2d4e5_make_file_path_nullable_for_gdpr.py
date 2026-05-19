"""make_file_path_nullable_for_gdpr

Allow file_path to be NULL on documents and document_versions so that
the GDPR Art.17 physical deletion job can null the field after erasing
the file from disk while preserving the record as an audit skeleton.

Revision ID: c3f8a1b2d4e5
Revises: a7e1d4f88c20
Create Date: 2026-05-16 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "c3f8a1b2d4e5"
down_revision: Union[str, Sequence[str], None] = "a7e1d4f88c20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("documents") as batch_op:
        batch_op.alter_column(
            "file_path",
            existing_type=sa.String(),
            nullable=True,
        )

    with op.batch_alter_table("document_versions") as batch_op:
        batch_op.alter_column(
            "file_path",
            existing_type=sa.String(),
            nullable=True,
        )


def downgrade() -> None:
    # Downgrade will fail if any rows have NULL file_path; callers must
    # ensure data is clean before reverting.
    with op.batch_alter_table("document_versions") as batch_op:
        batch_op.alter_column(
            "file_path",
            existing_type=sa.String(),
            nullable=False,
        )

    with op.batch_alter_table("documents") as batch_op:
        batch_op.alter_column(
            "file_path",
            existing_type=sa.String(),
            nullable=False,
        )
