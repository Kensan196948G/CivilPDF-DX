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


def _missing_columns(bind, table: str) -> set[str]:
    import sqlalchemy as sa

    inspector = sa.inspect(bind)
    if not inspector.has_table(table):
        return set()
    return {c["name"] for c in inspector.get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    doc_cols = _missing_columns(bind, "documents")
    version_cols = _missing_columns(bind, "document_versions")

    # Document: ReviewSidecar fields (feature #1)
    if "review_sidecar" not in doc_cols:
        op.add_column(
            "documents", sa.Column("review_sidecar", sa.JSON(), nullable=True)
        )
    if "review_sidecar_imported_at" not in doc_cols:
        op.add_column(
            "documents",
            sa.Column(
                "review_sidecar_imported_at",
                sa.DateTime(timezone=True),
                nullable=True,
            ),
        )

    # Document: revision management (feature #2)
    if "revision" not in doc_cols:
        op.add_column("documents", sa.Column("revision", sa.String(), nullable=True))
    if "revision_note" not in doc_cols:
        op.add_column(
            "documents", sa.Column("revision_note", sa.String(), nullable=True)
        )

    # Document: flatten gate (feature #3)
    if "is_flattened" not in doc_cols:
        op.add_column(
            "documents",
            sa.Column(
                "is_flattened",
                sa.Boolean(),
                nullable=True,
                server_default=sa.text("false"),
            ),
        )
    if "flattened_verified_at" not in doc_cols:
        op.add_column(
            "documents",
            sa.Column(
                "flattened_verified_at", sa.DateTime(timezone=True), nullable=True
            ),
        )
    if "flattened_hash" not in doc_cols:
        op.add_column(
            "documents", sa.Column("flattened_hash", sa.String(), nullable=True)
        )

    # DocumentVersion: editor integration fields (feature #2)
    if "revision" not in version_cols:
        op.add_column(
            "document_versions", sa.Column("revision", sa.String(), nullable=True)
        )
    if "revision_note" not in version_cols:
        op.add_column(
            "document_versions", sa.Column("revision_note", sa.String(), nullable=True)
        )
    if "is_from_editor" not in version_cols:
        op.add_column(
            "document_versions",
            sa.Column(
                "is_from_editor",
                sa.Boolean(),
                nullable=True,
                server_default=sa.text("false"),
            ),
        )
    if "editor_session_id" not in version_cols:
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
