"""add_organizations_table_and_fks

Revision ID: f6f34ef9e5bd
Revises: c3f8a1b2d4e5
Create Date: 2026-06-03 19:53:02.418670

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f6f34ef9e5bd"
down_revision: Union[str, Sequence[str], None] = "c3f8a1b2d4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _missing_columns(bind, table: str) -> set[str]:
    inspector = sa.inspect(bind)
    if not inspector.has_table(table):
        return set()
    return {c["name"] for c in inspector.get_columns(table)}


def _create_audit_logs_table() -> None:
    """Create audit_logs for DBs that pre-date b669f56cdac7's real DDL.

    Databases that were partially migrated by the original (no-op) b669
    revision can sit at c3f8a1b2d4e5 with organizations/retention_policies
    already present but audit_logs still missing (Issue #109). This helper
    makes the remaining chain self-healing in that state.
    """
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


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()

    # organizations
    if not sa.inspect(bind).has_table("organizations"):
        op.create_table(
            "organizations",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("code", sa.String(), nullable=False),
            sa.Column(
                "org_type",
                sa.Enum(
                    "HEADQUARTERS",
                    "BRANCH",
                    "SITE_OFFICE",
                    "MOBILE",
                    name="orgtype",
                ),
                nullable=False,
            ),
            sa.Column("parent_id", sa.String(), nullable=True),
            sa.Column("path", sa.String(), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("(CURRENT_TIMESTAMP)"),
                nullable=True,
            ),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(
                ["parent_id"],
                ["organizations.id"],
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("code"),
        )

    # retention_policies
    if not sa.inspect(bind).has_table("retention_policies"):
        op.create_table(
            "retention_policies",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("category", sa.String(), nullable=False),
            sa.Column("document_type", sa.String(), nullable=True),
            sa.Column("retention_years", sa.Integer(), nullable=False),
            sa.Column("is_permanent", sa.Boolean(), nullable=True),
            sa.Column("auto_archive", sa.Boolean(), nullable=True),
            sa.Column("auto_delete", sa.Boolean(), nullable=True),
            sa.Column("archive_grace_days", sa.Integer(), nullable=True),
            sa.Column("legal_basis", sa.Text(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("(CURRENT_TIMESTAMP)"),
                nullable=True,
            ),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("name"),
        )

    # audit_logs — exists since b669f56cdac7 on fresh DBs, or was created by
    # Base.metadata.create_all on legacy DBs. Partially migrated DBs may still
    # lack the table, so create it before touching the hash-chain columns.
    if not sa.inspect(bind).has_table("audit_logs"):
        _create_audit_logs_table()
    else:
        audit_cols = _missing_columns(bind, "audit_logs")
        for name, column in (
            (
                "sequence_number",
                sa.Column("sequence_number", sa.Integer(), nullable=True),
            ),
            ("record_hash", sa.Column("record_hash", sa.String(), nullable=True)),
            ("prev_hash", sa.Column("prev_hash", sa.String(), nullable=True)),
        ):
            if name not in audit_cols:
                op.add_column("audit_logs", column)
        if not sa.inspect(bind).has_index(
            "audit_logs", "ix_audit_logs_sequence_number"
        ):
            op.create_index(
                op.f("ix_audit_logs_sequence_number"),
                "audit_logs",
                ["sequence_number"],
                unique=False,
            )

    # consent_records
    if not sa.inspect(bind).has_table("consent_records"):
        op.create_table(
            "consent_records",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("user_id", sa.String(), nullable=False),
            sa.Column("consent_type", sa.String(), nullable=False),
            sa.Column("version", sa.String(), nullable=False),
            sa.Column("granted", sa.Boolean(), nullable=False),
            sa.Column("ip_address", sa.String(), nullable=True),
            sa.Column("user_agent", sa.String(), nullable=True),
            sa.Column("source", sa.String(), nullable=True),
            sa.Column("disclosed_purpose", sa.Text(), nullable=True),
            sa.Column("disclosed_retention_period", sa.String(), nullable=True),
            sa.Column("disclosed_third_parties", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("(CURRENT_TIMESTAMP)"),
                nullable=True,
            ),
            sa.ForeignKeyConstraint(
                ["user_id"],
                ["users.id"],
            ),
            sa.PrimaryKeyConstraint("id"),
        )
    for index, col in (
        ("ix_consent_records_consent_type", "consent_type"),
        ("ix_consent_records_created_at", "created_at"),
        ("ix_consent_records_user_id", "user_id"),
    ):
        if not sa.inspect(bind).has_index("consent_records", index):
            op.create_index(op.f(index), "consent_records", [col], unique=False)

    # documents — add columns/FK idempotently (legacy create_all DBs already
    # have these columns; batch mode is required for SQLite FK creation).
    doc_cols = _missing_columns(bind, "documents")
    _DOC_COLUMNS = [
        (
            "pdfa_validation_result",
            sa.Column("pdfa_validation_result", sa.JSON(), nullable=True),
        ),
        (
            "timestamp_verified_at",
            sa.Column(
                "timestamp_verified_at", sa.DateTime(timezone=True), nullable=True
            ),
        ),
        ("timestamp_hash", sa.Column("timestamp_hash", sa.String(), nullable=True)),
        ("timestamp_token", sa.Column("timestamp_token", sa.Text(), nullable=True)),
        (
            "timestamp_tsa_url",
            sa.Column("timestamp_tsa_url", sa.String(), nullable=True),
        ),
        (
            "retention_policy_id",
            sa.Column("retention_policy_id", sa.String(), nullable=True),
        ),
        (
            "retention_expires_at",
            sa.Column(
                "retention_expires_at", sa.DateTime(timezone=True), nullable=True
            ),
        ),
        ("is_archived", sa.Column("is_archived", sa.Boolean(), nullable=True)),
        (
            "archived_at",
            sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        ),
        (
            "deletion_requested_at",
            sa.Column(
                "deletion_requested_at", sa.DateTime(timezone=True), nullable=True
            ),
        ),
        (
            "iso19650_originator",
            sa.Column("iso19650_originator", sa.String(), nullable=True),
        ),
        (
            "iso19650_functional_breakdown",
            sa.Column("iso19650_functional_breakdown", sa.String(), nullable=True),
        ),
        ("iso19650_form", sa.Column("iso19650_form", sa.String(), nullable=True)),
        (
            "iso19650_discipline",
            sa.Column("iso19650_discipline", sa.String(), nullable=True),
        ),
        ("iso19650_number", sa.Column("iso19650_number", sa.String(), nullable=True)),
    ]
    doc_fk_names = {fk["name"] for fk in sa.inspect(bind).get_foreign_keys("documents")}
    with op.batch_alter_table("documents") as batch_op:
        for name, column in _DOC_COLUMNS:
            if name not in doc_cols:
                batch_op.add_column(column)
        if "fk_documents_retention_policy" not in doc_fk_names:
            batch_op.create_foreign_key(
                "fk_documents_retention_policy",
                "retention_policies",
                ["retention_policy_id"],
                ["id"],
            )

    # projects / users — organization_id FK
    for table, fk_name in (
        ("projects", "fk_projects_organization"),
        ("users", "fk_users_organization"),
    ):
        cols = _missing_columns(bind, table)
        fk_names = {fk["name"] for fk in sa.inspect(bind).get_foreign_keys(table)}
        with op.batch_alter_table(table) as batch_op:
            if "organization_id" not in cols:
                batch_op.add_column(
                    sa.Column("organization_id", sa.String(), nullable=True)
                )
            if fk_name not in fk_names:
                batch_op.create_foreign_key(
                    fk_name, "organizations", ["organization_id"], ["id"]
                )


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint("fk_users_organization", type_="foreignkey")
        batch_op.drop_column("organization_id")
    with op.batch_alter_table("projects") as batch_op:
        batch_op.drop_constraint("fk_projects_organization", type_="foreignkey")
        batch_op.drop_column("organization_id")
    with op.batch_alter_table("documents") as batch_op:
        batch_op.drop_constraint("fk_documents_retention_policy", type_="foreignkey")
        batch_op.drop_column("iso19650_number")
        batch_op.drop_column("iso19650_discipline")
        batch_op.drop_column("iso19650_form")
        batch_op.drop_column("iso19650_functional_breakdown")
        batch_op.drop_column("iso19650_originator")
        batch_op.drop_column("deletion_requested_at")
        batch_op.drop_column("archived_at")
        batch_op.drop_column("is_archived")
        batch_op.drop_column("retention_expires_at")
        batch_op.drop_column("retention_policy_id")
        batch_op.drop_column("timestamp_tsa_url")
        batch_op.drop_column("timestamp_token")
        batch_op.drop_column("timestamp_hash")
        batch_op.drop_column("timestamp_verified_at")
        batch_op.drop_column("pdfa_validation_result")
    op.drop_index(op.f("ix_consent_records_user_id"), table_name="consent_records")
    op.drop_index(op.f("ix_consent_records_created_at"), table_name="consent_records")
    op.drop_index(op.f("ix_consent_records_consent_type"), table_name="consent_records")
    op.drop_table("consent_records")
    op.drop_index(op.f("ix_audit_logs_sequence_number"), table_name="audit_logs")
    op.drop_column("audit_logs", "prev_hash")
    op.drop_column("audit_logs", "record_hash")
    op.drop_column("audit_logs", "sequence_number")
    op.drop_table("retention_policies")
    op.drop_table("organizations")
    # ### end Alembic commands ###
