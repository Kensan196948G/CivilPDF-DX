"""Enforce UNIQUE on audit_logs.sequence_number to protect the hash chain.

create_chained_audit_log() (services/audit_chain_service.py) read the last
sequence_number and computed next_seq = last + 1 without a row lock or a DB
constraint backing it. Two concurrent writers could both read the same last
record and insert the same sequence_number, silently breaking the
tamper-evident hash chain that the audit/compliance feature relies on. This
migration adds the missing UNIQUE constraint (defense in depth: paired with
the SELECT ... FOR UPDATE added in the same change to services/
audit_chain_service.py, which prevents the race instead of just detecting
it after the fact). NULLs remain unrestricted (pre-chain legacy rows, if
any) since UNIQUE allows multiple NULLs on every supported backend here.

Revision ID: m3n4o5p6q7r8
Revises: l2m3n4o5p6q7
Create Date: 2026-09-18
"""

from alembic import op
import sqlalchemy as sa


revision = "m3n4o5p6q7r8"
down_revision = "l2m3n4o5p6q7"
branch_labels = None
depends_on = None

# Kept as the same name SQLAlchemy's Column(index=True) auto-generates
# (ix_<table>_<column>), so Base.metadata.create_all() (used by tests) and
# this Alembic migration (used in deployed environments) agree on the name.
_INDEX_NAME = "ix_audit_logs_sequence_number"


def upgrade() -> None:
    bind = op.get_bind()

    dup_rows = bind.execute(
        sa.text(
            "SELECT sequence_number, COUNT(*) c FROM audit_logs "
            "WHERE sequence_number IS NOT NULL "
            "GROUP BY sequence_number HAVING COUNT(*) > 1"
        )
    ).fetchall()
    if dup_rows:
        raise RuntimeError(
            f"Cannot add UNIQUE constraint: {len(dup_rows)} duplicate "
            "sequence_number value(s) already exist in audit_logs "
            "(hash chain already corrupted) — resolve manually before "
            "re-running this migration."
        )

    inspector = sa.inspect(bind)
    existing = {ix["name"] for ix in inspector.get_indexes("audit_logs")}
    if _INDEX_NAME in existing:
        op.drop_index(_INDEX_NAME, table_name="audit_logs")
    op.create_index(_INDEX_NAME, "audit_logs", ["sequence_number"], unique=True)


def downgrade() -> None:
    op.drop_index(_INDEX_NAME, table_name="audit_logs")
    op.create_index(_INDEX_NAME, "audit_logs", ["sequence_number"], unique=False)
