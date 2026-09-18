"""Add performance indexes on documents(project_id/owner_id/status).

list_documents / export_documents (api/documents.py) filter on these columns
on every call, but only users.email had an index before this migration
(docs/database-design.md §6 listed them as "recommended, not implemented").
Foreign keys do not get an implicit index on PostgreSQL, so these filters
were doing full table scans.

Revision ID: l2m3n4o5p6q7
Revises: k1l2m3n4o5p6
Create Date: 2026-09-18
"""

from alembic import op
import sqlalchemy as sa


revision = "l2m3n4o5p6q7"
down_revision = "k1l2m3n4o5p6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = {ix["name"] for ix in inspector.get_indexes("documents")}

    if "ix_documents_project_id" not in existing:
        op.create_index("ix_documents_project_id", "documents", ["project_id"])
    if "ix_documents_owner_id" not in existing:
        op.create_index("ix_documents_owner_id", "documents", ["owner_id"])
    if "ix_documents_status" not in existing:
        op.create_index("ix_documents_status", "documents", ["status"])


def downgrade() -> None:
    # Only drop indexes this migration's upgrade() actually owns creating
    # (guarded the same way as upgrade(), in case a partial run left some
    # already present).
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = {ix["name"] for ix in inspector.get_indexes("documents")}

    if "ix_documents_status" in existing:
        op.drop_index("ix_documents_status", table_name="documents")
    if "ix_documents_owner_id" in existing:
        op.drop_index("ix_documents_owner_id", table_name="documents")
    if "ix_documents_project_id" in existing:
        op.drop_index("ix_documents_project_id", table_name="documents")
