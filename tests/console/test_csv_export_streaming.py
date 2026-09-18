"""CSV export hardening: bounded streaming, no N+1, hard row ceiling.

Regression context (2026-09-18 production-readiness assessment): the export
endpoints called ``.all()`` and ``csv_stream_response`` built the whole file in
a single ``StringIO`` before handing it to ``StreamingResponse``. The result was
neither streamed nor bounded, and ``doc.project`` / ``doc.owner`` were loaded
lazily per row (N+1). These tests pin all three properties.
"""

import io

import pytest
from sqlalchemy import event

from api.csv_export import (
    MAX_EXPORT_ROWS,
    _iter_csv_chunks,
    csv_stream_response,
    sanitize_cell,
)


def _make_pdf_bytes() -> bytes:
    return b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n%%EOF"


def _create_project(client, token: str, name: str = "Streaming Export") -> str:
    resp = client.post(
        "/api/v1/projects/",
        json={"name": name, "code": f"STR-{abs(hash(name)) % 100000}"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def _upload_doc(client, token: str, project_id: str, title: str) -> str:
    resp = client.post(
        "/api/v1/documents/",
        data={"project_id": project_id, "title": title},
        files={
            "file": (f"{title}.pdf", io.BytesIO(_make_pdf_bytes()), "application/pdf")
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


class TestChunkedCsvStreaming:
    def test_large_export_is_emitted_in_multiple_bounded_chunks(self):
        """Peak memory must be bounded by chunk_rows, not by the row count."""
        rows = ([f"doc-{i}", f"name-{i}", "x" * 50] for i in range(2500))
        chunks = list(_iter_csv_chunks(["id", "title", "note"], rows, 100))

        assert len(chunks) == 25, f"expected 25 chunks, got {len(chunks)}"
        # Header + 100 rows per chunk stays far below the ~130KB full document.
        assert max(len(c) for c in chunks) < 20000
        assert sum(len(c) for c in chunks) > 100000

    def test_concatenated_chunks_reproduce_the_full_csv(self):
        rows = [[i, f"タイトル{i}"] for i in range(250)]
        streamed = b"".join(_iter_csv_chunks(["id", "title"], rows, 40))

        import csv as _csv

        text = streamed.decode("utf-8-sig")
        # \r\n line terminator; trailing terminator yields one empty tail field.
        parsed = list(_csv.reader(io.StringIO(text)))
        assert parsed[0] == ["id", "title"]
        assert len(parsed) == 251  # header + 250 rows
        assert parsed[1] == ["0", "タイトル0"]
        assert parsed[250] == ["249", "タイトル249"]

    def test_exact_multiple_of_chunk_size_has_no_empty_trailing_chunk(self):
        rows = [[i] for i in range(10)]
        chunks = list(_iter_csv_chunks(["id"], rows, 5))
        assert len(chunks) == 2
        assert all(c.strip() for c in chunks)

    def test_empty_export_still_emits_the_header_row(self):
        chunks = list(_iter_csv_chunks(["id", "title"], [], 100))
        assert len(chunks) == 1
        assert chunks[0].decode("utf-8-sig") == "id,title\r\n"

    def test_utf8_bom_is_present_once(self):
        chunks = list(_iter_csv_chunks(["id"], [[1], [2]], 1))
        assert chunks[0].startswith("\ufeff".encode())
        assert not any(c.startswith("\ufeff".encode()) for c in chunks[1:])

    def test_formula_injection_is_neutralised_per_cell(self):
        assert sanitize_cell("=cmd()|calc") == "'=cmd()|calc"
        assert sanitize_cell("+1") == "'+1"
        assert sanitize_cell("-1") == "'-1"
        assert sanitize_cell("@x") == "'@x"
        assert sanitize_cell("安全") == "安全"
        assert sanitize_cell(None) == ""

    def test_rejects_a_non_positive_chunk_size(self):
        with pytest.raises(ValueError):
            list(_iter_csv_chunks(["id"], [[1]], 0))

    def test_response_helper_returns_a_streaming_response(self):
        from fastapi.responses import StreamingResponse

        resp = csv_stream_response(["id"], [[1]], "test.csv")
        assert isinstance(resp, StreamingResponse)
        assert resp.headers["content-disposition"] == 'attachment; filename="test.csv"'
        assert resp.headers["x-content-type-options"] == "nosniff"


def _export_select_statements(client, token: str, db_session, path: str) -> list[str]:
    """Run an export and return the SELECT statements it issued."""
    bind = db_session.get_bind()
    statements: list[str] = []

    def _record(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(bind, "before_cursor_execute", _record)
    try:
        resp = client.get(path, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200, resp.text
    finally:
        event.remove(bind, "before_cursor_execute", _record)

    return [s for s in statements if s.lstrip().upper().startswith("SELECT")]


def _seed_documents(db_session, count: int, prefix: str) -> None:
    """Seed ``count`` documents that each belong to a *distinct* project/owner.

    Distinct relations matter: SQLAlchemy's identity map de-duplicates lazy
    loads that resolve to the same row, so documents sharing one project and one
    owner hide an N+1 completely.
    """
    from auth.jwt import get_password_hash
    from models.document import Document, DocumentStatus, DocumentType
    from models.user import Project, User, UserRole, UserStatus

    for i in range(count):
        owner = User(
            email=f"{prefix}-{i}@example.com",
            username=f"{prefix}-{i}",
            full_name=f"Owner {i}",
            hashed_password=get_password_hash("Seed1234!"),
            role=UserRole.VIEWER,
            status=UserStatus.ACTIVE,
        )
        project = Project(name=f"{prefix} project {i}", code=f"{prefix}-{i}")
        db_session.add_all([owner, project])
        db_session.flush()
        db_session.add(
            Document(
                project_id=project.id,
                owner_id=owner.id,
                title=f"{prefix}-doc-{i}",
                filename=f"{prefix}-{i}.pdf",
                document_type=DocumentType.OTHER,
                status=DocumentStatus.DRAFT,
                file_path=f"/tmp/{prefix}-{i}.pdf",
                file_size=1,
                mime_type="application/pdf",
            )
        )
    db_session.commit()


class TestDocumentExportScalability:
    def test_document_export_query_count_does_not_grow_with_rows(
        self, client, admin_token, db_session
    ):
        """N+1 proof: more distinct projects/owners must not add per-row queries."""
        _seed_documents(db_session, 2, "nplus1a")
        baseline = len(
            _export_select_statements(
                client, admin_token, db_session, "/api/v1/documents/export.csv"
            )
        )

        _seed_documents(db_session, 8, "nplus1b")
        expanded = len(
            _export_select_statements(
                client, admin_token, db_session, "/api/v1/documents/export.csv"
            )
        )

        assert expanded <= baseline + 1, (
            "SELECT count grew with the number of distinct projects/owners, so "
            "the export still loads relations per row: 2 documents -> "
            f"{baseline} SELECTs, 10 documents -> {expanded} SELECTs"
        )

    def test_document_export_returns_every_row_across_distinct_projects(
        self, client, admin_token, db_session
    ):
        _seed_documents(db_session, 30, "streamrows")

        resp = client.get(
            "/api/v1/documents/export.csv",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        text = resp.content.decode("utf-8-sig")
        assert text.count("\r\n") == 31  # header + 30 rows
        for i in range(30):
            assert f"streamrows-doc-{i}" in text
            # The joined project/owner values must be present, not blank.
            assert f"streamrows project {i}" in text
            assert f"streamrows-{i}@example.com" in text

    def test_document_export_rejects_result_sets_above_the_ceiling(
        self, client, admin_token, db_session, monkeypatch
    ):
        monkeypatch.setattr("api.csv_export.MAX_EXPORT_ROWS", 2)
        project_id = _create_project(client, admin_token, "Ceiling")
        for i in range(3):
            _upload_doc(client, admin_token, project_id, f"ceil-{i}")

        resp = client.get(
            f"/api/v1/documents/export.csv?project_id={project_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 413
        assert "上限" in resp.json()["detail"]


class TestAuditExportScalability:
    def test_audit_export_rejects_result_sets_above_the_ceiling(
        self, client, admin_token, db_session, monkeypatch
    ):
        from services.audit_chain_service import create_chained_audit_log

        monkeypatch.setattr("api.csv_export.MAX_EXPORT_ROWS", 3)
        for i in range(4):
            create_chained_audit_log(
                db_session, user_id=None, action=f"ceiling.{i}", detail="x"
            )

        resp = client.get(
            "/api/v1/audit-logs/export.csv",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 413
        assert "上限" in resp.json()["detail"]

    def test_audit_export_streams_all_rows_below_the_ceiling(
        self, client, admin_token, db_session
    ):
        from services.audit_chain_service import create_chained_audit_log

        for i in range(25):
            create_chained_audit_log(
                db_session, user_id=None, action=f"streamed.{i}", detail="x"
            )

        resp = client.get(
            "/api/v1/audit-logs/export.csv",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        text = resp.content.decode("utf-8-sig")
        for i in range(25):
            assert f"streamed.{i}" in text

    def test_default_ceiling_still_permits_a_normal_export(
        self, client, admin_token, db_session
    ):
        """Guard against the ceiling being lowered to something unusable."""
        assert MAX_EXPORT_ROWS >= 10000
