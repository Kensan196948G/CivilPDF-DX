"""Add the ocr_jobs table so extraction jobs survive restarts and workers.

OCR jobs were held in a module-level dict in ``api/ocr.py``. That made them
invisible to every other process: ``docker-compose.prod.yml`` starts uvicorn with
``--workers ${UVICORN_WORKERS:-4}`` (2 in ``.env``), so
``GET /ocr/jobs/{job_id}`` returned 404 whenever the poll landed on a worker
other than the one that created the job, and every restart dropped all results.

The table is additive and safe for existing deployments: no existing column or
row is touched, so the upgrade is a plain CREATE TABLE.

Revision ID: o5p6q7r8s9t0
Revises: n4o5p6q7r8s9
Create Date: 2026-09-18
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "o5p6q7r8s9t0"
down_revision: Union[str, None] = "n4o5p6q7r8s9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    # A create_all-era database already has this table (and the indexes
    # SQLAlchemy generates for index=True), so creating it again would abort the
    # upgrade. Same guard as the other additive migrations in this chain.
    if sa.inspect(bind).has_table("ocr_jobs"):
        return

    op.create_table(
        "ocr_jobs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "document_id",
            sa.String(),
            sa.ForeignKey("documents.id"),
            nullable=False,
        ),
        sa.Column(
            "requested_by", sa.String(), sa.ForeignKey("users.id"), nullable=True
        ),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("engine", sa.String(), nullable=False),
        sa.Column("language", sa.String(), nullable=False),
        sa.Column("enable_vertical", sa.Boolean(), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("pages", sa.JSON(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_ocr_jobs_document_id", "ocr_jobs", ["document_id"])
    op.create_index("ix_ocr_jobs_requested_by", "ocr_jobs", ["requested_by"])
    op.create_index("ix_ocr_jobs_created_at", "ocr_jobs", ["created_at"])


def downgrade() -> None:
    bind = op.get_bind()
    if not sa.inspect(bind).has_table("ocr_jobs"):
        return
    op.drop_index("ix_ocr_jobs_created_at", table_name="ocr_jobs")
    op.drop_index("ix_ocr_jobs_requested_by", table_name="ocr_jobs")
    op.drop_index("ix_ocr_jobs_document_id", table_name="ocr_jobs")
    op.drop_table("ocr_jobs")
