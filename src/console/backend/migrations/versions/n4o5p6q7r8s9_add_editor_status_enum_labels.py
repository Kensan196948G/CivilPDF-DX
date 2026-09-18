"""Add the missing UPPERCASE labels for the editor-integration document statuses.

Root cause (found 2026-09-18 while verifying the PostgreSQL schema against the
ORM models):

``models/document.py`` declares ``DocumentStatus`` as a ``(str, Enum)`` whose
members are ``EDITOR_DRAFT`` / ``EDITOR_REVIEWED`` / ``FINALIZED``.
``Column(Enum(DocumentStatus))`` persists the enum member **names** (uppercase)
unless ``values_callable`` is supplied, so the ORM sends ``'EDITOR_DRAFT'``,
``'EDITOR_REVIEWED'`` and ``'FINALIZED'`` to the database.

Migration ``f2b3c4d5e6f7`` added those three statuses to the PostgreSQL enum
using their lowercase **values** instead, so the labels the application
actually sends were never created:

    PG enum documentstatus = DRAFT,PENDING_REVIEW,APPROVED,REJECTED,ARCHIVED,
                            editor_draft,editor_reviewed,finalized
    ORM emits              = DRAFT,PENDING_REVIEW,APPROVED,REJECTED,ARCHIVED,
                            EDITOR_DRAFT,EDITOR_REVIEWED,FINALIZED

Impact: on PostgreSQL every write of those statuses failed with
``invalid input value for enum documentstatus: "EDITOR_DRAFT"``. That breaks
the Editor integration flow on the PostgreSQL/Neon production deployment
(sidecar import -> EDITOR_DRAFT/EDITOR_REVIEWED, flatten-check -> FINALIZED).
SQLite stores ``Enum`` columns as plain VARCHAR, so CI (SQLite) stayed green —
the defect was invisible to the entire test suite.

This migration adds the three missing uppercase labels so the enum matches what
the ORM emits and the already-stored data (which uses names) stays valid. The
lowercase labels introduced by ``f2b3c4d5e6f7`` are unused by the ORM and are
left in place because PostgreSQL cannot drop enum values.

Revision ID: n4o5p6q7r8s9
Revises: m3n4o5p6q7r8
Create Date: 2026-09-18
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "n4o5p6q7r8s9"
down_revision: Union[str, None] = "m3n4o5p6q7r8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Member NAMES emitted by Column(Enum(DocumentStatus)).
_MISSING_LABELS = ("EDITOR_DRAFT", "EDITOR_REVIEWED", "FINALIZED")


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        # SQLite (and other non-native-enum backends) store Enum columns as
        # VARCHAR, so the new members are already accepted at the model layer.
        return

    # ALTER TYPE ... ADD VALUE cannot run inside the migration's transaction
    # block on PostgreSQL.
    with op.get_context().autocommit_block():
        for label in _MISSING_LABELS:
            op.execute(
                sa.text(f"ALTER TYPE documentstatus ADD VALUE IF NOT EXISTS '{label}'")
            )


def downgrade() -> None:
    # PostgreSQL does not support removing enum values (same convention as
    # f2b3c4d5e6f7). Rows holding these labels must be migrated away before a
    # downgrade could be meaningful.
    pass
