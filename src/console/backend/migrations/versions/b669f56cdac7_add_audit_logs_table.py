"""add_audit_logs_table

Revision ID: b669f56cdac7
Revises: 4f3c22038863
Create Date: 2026-05-11 08:15:10.554410

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "b669f56cdac7"
down_revision: Union[str, Sequence[str], None] = "4f3c22038863"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the append-only audit_logs table with SHA-256 hash chain.

    This revision was originally a no-op because the table was created by
    Base.metadata.create_all before Alembic took over. For fresh databases
    (e.g. `alembic upgrade head` from an empty DB) the table must exist
    before later revisions reference it (Issue #109).
    """
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("audit_logs"):
        return

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=True),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("resource_type", sa.String(), nullable=True),
        sa.Column("resource_id", sa.String(), nullable=True),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=True,
        ),
        # Hash chain fields (NIS2 / ISO 19650-5 / J-SOX)
        sa.Column("sequence_number", sa.Integer(), nullable=True),
        sa.Column("record_hash", sa.String(), nullable=True),
        sa.Column("prev_hash", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_logs_action"), "audit_logs", ["action"])
    op.create_index(
        op.f("ix_audit_logs_resource_type"), "audit_logs", ["resource_type"]
    )
    op.create_index(op.f("ix_audit_logs_created_at"), "audit_logs", ["created_at"])
    op.create_index(
        op.f("ix_audit_logs_sequence_number"),
        "audit_logs",
        ["sequence_number"],
    )


def downgrade() -> None:
    """Deliberately do not drop audit_logs.

    audit_logs is an append-only evidence store. On legacy databases the
    table predates Alembic (created by Base.metadata.create_all), so this
    revision must never own its destruction. f6f34ef9e5bd's downgrade still
    removes the hash-chain columns it added on legacy DBs; fresh databases
    keep the full table after downgrade, which is the safe choice for
    evidence retention.
    """
    pass
