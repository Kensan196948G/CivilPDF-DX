"""extend_document_status_enum

Revision ID: f2b3c4d5e6f7
Revises: e1a2b3c4d5e6
Create Date: 2026-06-21 12:01:00.000000

PostgreSQL: ALTER TYPE ... ADD VALUE IF NOT EXISTS (non-transactional).
SQLite: no-op (Enum stored as VARCHAR, new values accepted at model layer).

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f2b3c4d5e6f7"
down_revision: Union[str, None] = "e1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NEW_VALUES = ("editor_draft", "editor_reviewed", "finalized")


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        # ADD VALUE must run outside a transaction block.
        with op.get_context().autocommit_block():
            for val in _NEW_VALUES:
                op.execute(
                    sa.text(
                        f"ALTER TYPE documentstatus ADD VALUE IF NOT EXISTS '{val}'"
                    )
                )


def downgrade() -> None:
    # PostgreSQL does not support DROP VALUE from an Enum.
    # Rows using the new values must be migrated away before downgrading.
    pass
