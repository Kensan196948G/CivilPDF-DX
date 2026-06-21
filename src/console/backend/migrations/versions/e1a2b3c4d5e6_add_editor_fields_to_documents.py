"""add_editor_fields_to_documents

Revision ID: e1a2b3c4d5e6
Revises: f6f34ef9e5bd
Create Date: 2026-06-21 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e1a2b3c4d5e6"
down_revision: Union[str, None] = "f6f34ef9e5bd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Document: ReviewSidecar fields (feature #1)
    op.add_column("documents", sa.Column("review_sidecar", sa.JSON(), nullable=True))
    op.add_column(
        "documents",
        sa.Column(
            "review_sidecar_imported_at", sa.DateTime(timezone=True), nullable=True
        ),
    )

    # Document: revision management (feature #2)
    op.add_column("documents", sa.Column("revision", sa.String(), nullable=True))
    op.add_column("documents", sa.Column("revision_note", sa.String(), nullable=True))

    # Document: flatten gate (feature #3)
    op.add_column(
        "documents",
        sa.Column(
            "is_flattened", sa.Boolean(), nullable=True, server_default=sa.text("false")
        ),
    )
    op.add_column(
        "documents",
        sa.Column("flattened_verified_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("documents", sa.Column("flattened_hash", sa.String(), nullable=True))

    # DocumentVersion: editor integration fields (feature #2)
    op.add_column(
        "document_versions", sa.Column("revision", sa.String(), nullable=True)
    )
    op.add_column(
        "document_versions", sa.Column("revision_note", sa.String(), nullable=True)
    )
    op.add_column(
        "document_versions",
        sa.Column(
            "is_from_editor",
            sa.Boolean(),
            nullable=True,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "document_versions",
        sa.Column("editor_session_id", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("document_versions", "editor_session_id")
    op.drop_column("document_versions", "is_from_editor")
    op.drop_column("document_versions", "revision_note")
    op.drop_column("document_versions", "revision")

    op.drop_column("documents", "flattened_hash")
    op.drop_column("documents", "flattened_verified_at")
    op.drop_column("documents", "is_flattened")
    op.drop_column("documents", "revision_note")
    op.drop_column("documents", "revision")
    op.drop_column("documents", "review_sidecar_imported_at")
    op.drop_column("documents", "review_sidecar")
