"""Tests for electronic delivery ZIP generation (Phase 8 P3 / Phase 9 P1).

Covers:
- Readiness check API (GET .../check)
- ZIP generation API (POST .../electronic-delivery)
- ZIP content validation (folder structure, INDEX.XML)
- Auth / permission guards
- Real file inclusion (Phase 9 P1: file_path set → actual bytes in ZIP)
- Missing file fallback (Phase 9 P1: file_path missing → empty placeholder)
"""

import io
import sys
import os
import tempfile
import zipfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src/console/backend"))

import pytest
from fastapi.testclient import TestClient

from models.document import Document, DocumentStatus, DocumentType
from models.user import Project, User, UserRole, UserStatus


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _create_project(db, code: str = "TEST001", name: str = "テスト工事") -> Project:
    proj = Project(name=name, code=code, description="テスト工事")
    db.add(proj)
    db.commit()
    db.refresh(proj)
    return proj


def _create_document(
    db,
    project_id: str,
    owner_id: str,
    title: str = "テスト図面",
    doc_type: DocumentType = DocumentType.DRAWING,
    filename: str = "test.pdf",
    is_pdfa: bool = True,
) -> Document:
    doc = Document(
        title=title,
        document_type=doc_type,
        status=DocumentStatus.APPROVED,
        filename=filename,
        file_path=None,
        file_size=1024,
        is_pdfa=is_pdfa,
        project_id=project_id,
        owner_id=owner_id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


# ─── Check endpoint ───────────────────────────────────────────────────────────


def test_check_delivery_empty_project(client: TestClient, admin_token: str, db_session):
    proj = _create_project(db_session)
    resp = client.get(
        f"/api/v1/projects/{proj.id}/electronic-delivery/check",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ready"] is False
    assert data["document_count"] == 0
    assert data["pdfa_compliant_count"] == 0
    assert data["non_pdfa_documents"] == []
    assert any("文書が1件もありません" in w for w in data["warnings"])


def test_check_delivery_with_pdfa_documents(
    client: TestClient, admin_token: str, admin_user: User, db_session
):
    proj = _create_project(db_session)
    _create_document(db_session, proj.id, admin_user.id, is_pdfa=True)
    _create_document(db_session, proj.id, admin_user.id, title="図面2", is_pdfa=True)

    resp = client.get(
        f"/api/v1/projects/{proj.id}/electronic-delivery/check",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ready"] is True
    assert data["document_count"] == 2
    assert data["pdfa_compliant_count"] == 2
    assert data["non_pdfa_documents"] == []
    assert data["warnings"] == []


def test_check_delivery_non_pdfa_warning(
    client: TestClient, admin_token: str, admin_user: User, db_session
):
    proj = _create_project(db_session)
    _create_document(
        db_session, proj.id, admin_user.id, is_pdfa=False, filename="bad.pdf"
    )

    resp = client.get(
        f"/api/v1/projects/{proj.id}/electronic-delivery/check",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ready"] is True
    assert data["pdfa_compliant_count"] == 0
    assert len(data["non_pdfa_documents"]) == 1
    assert any("PDF/A" in w for w in data["warnings"])


def test_check_delivery_project_not_found(client: TestClient, admin_token: str):
    resp = client.get(
        "/api/v1/projects/nonexistent-id/electronic-delivery/check",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404


def test_check_delivery_requires_auth(client: TestClient, db_session):
    proj = _create_project(db_session)
    resp = client.get(f"/api/v1/projects/{proj.id}/electronic-delivery/check")
    assert resp.status_code == 401


# ─── ZIP generation endpoint ──────────────────────────────────────────────────


def test_generate_zip_empty_project(client: TestClient, admin_token: str, db_session):
    proj = _create_project(db_session)
    resp = client.post(
        f"/api/v1/projects/{proj.id}/electronic-delivery",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/zip"
    assert "attachment" in resp.headers["content-disposition"]
    assert ".zip" in resp.headers["content-disposition"]


def test_generate_zip_with_drawing(
    client: TestClient, admin_token: str, admin_user: User, db_session
):
    proj = _create_project(db_session)
    _create_document(db_session, proj.id, admin_user.id, doc_type=DocumentType.DRAWING)

    resp = client.post(
        f"/api/v1/projects/{proj.id}/electronic-delivery",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200

    zf = zipfile.ZipFile(io.BytesIO(resp.content))
    names = zf.namelist()
    assert any("INDEX.XML" in n for n in names)
    assert any("DRAWINGS/DRAW_0001.PDF" in n for n in names)


def test_generate_zip_folder_structure(
    client: TestClient, admin_token: str, admin_user: User, db_session
):
    proj = _create_project(db_session)
    _create_document(db_session, proj.id, admin_user.id, doc_type=DocumentType.DRAWING)
    _create_document(
        db_session, proj.id, admin_user.id, title="写真1", doc_type=DocumentType.PHOTO
    )
    _create_document(
        db_session,
        proj.id,
        admin_user.id,
        title="検査1",
        doc_type=DocumentType.INSPECTION,
    )

    resp = client.post(
        f"/api/v1/projects/{proj.id}/electronic-delivery",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200

    zf = zipfile.ZipFile(io.BytesIO(resp.content))
    names = zf.namelist()
    assert any("DRAWINGS/DRAW_0001.PDF" in n for n in names)
    assert any("PHOTO/PHOT_0001.PDF" in n for n in names)
    assert any("INSPECTION/INSP_0001.PDF" in n for n in names)


def test_generate_zip_contains_index_xml(
    client: TestClient, admin_token: str, admin_user: User, db_session
):
    proj = _create_project(db_session, code="SITE-007", name="国道7号改良工事")
    _create_document(db_session, proj.id, admin_user.id)

    resp = client.post(
        f"/api/v1/projects/{proj.id}/electronic-delivery",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    zf = zipfile.ZipFile(io.BytesIO(resp.content))
    xml_entries = [n for n in zf.namelist() if n.endswith("INDEX.XML")]
    assert len(xml_entries) == 1


def test_generate_zip_index_xml_content(
    client: TestClient, admin_token: str, admin_user: User, db_session
):
    proj = _create_project(db_session, code="PROJ-A1", name="河川改修工事")
    _create_document(db_session, proj.id, admin_user.id, title="平面図")

    resp = client.post(
        f"/api/v1/projects/{proj.id}/electronic-delivery",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    zf = zipfile.ZipFile(io.BytesIO(resp.content))
    xml_entry = next(n for n in zf.namelist() if n.endswith("INDEX.XML"))
    xml_content = zf.read(xml_entry).decode("utf-8")

    assert "工事管理情報" in xml_content
    assert "PROJ-A1" in xml_content
    assert "河川改修工事" in xml_content
    assert "CivilPDF-DX" in xml_content
    assert "平面図" in xml_content


def test_generate_zip_filename_sanitized(
    client: TestClient, admin_token: str, db_session
):
    proj = _create_project(db_session, code="工事/001", name="テスト")
    resp = client.post(
        f"/api/v1/projects/{proj.id}/electronic-delivery",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    disposition = resp.headers["content-disposition"]
    # Sanitized code must not contain slash or non-ASCII
    filename_part = disposition.split("filename=")[1].strip('"')
    assert "/" not in filename_part
    assert filename_part.isascii()


def test_generate_zip_multiple_docs_same_type(
    client: TestClient, admin_token: str, admin_user: User, db_session
):
    proj = _create_project(db_session)
    for i in range(3):
        _create_document(
            db_session,
            proj.id,
            admin_user.id,
            title=f"図面{i + 1}",
            doc_type=DocumentType.DRAWING,
        )

    resp = client.post(
        f"/api/v1/projects/{proj.id}/electronic-delivery",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    zf = zipfile.ZipFile(io.BytesIO(resp.content))
    drawing_files = [n for n in zf.namelist() if "DRAWINGS/DRAW_" in n]
    assert len(drawing_files) == 3
    assert any("DRAW_0001.PDF" in n for n in drawing_files)
    assert any("DRAW_0002.PDF" in n for n in drawing_files)
    assert any("DRAW_0003.PDF" in n for n in drawing_files)


def test_generate_zip_project_not_found(client: TestClient, admin_token: str):
    resp = client.post(
        "/api/v1/projects/nonexistent-id/electronic-delivery",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404


def test_generate_zip_requires_auth(client: TestClient, db_session):
    proj = _create_project(db_session)
    resp = client.post(f"/api/v1/projects/{proj.id}/electronic-delivery")
    assert resp.status_code == 401


def test_generate_zip_forbidden_for_viewer(
    client: TestClient, viewer_token: str, db_session
):
    proj = _create_project(db_session)
    resp = client.post(
        f"/api/v1/projects/{proj.id}/electronic-delivery",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert resp.status_code == 403


def test_generate_zip_response_headers(
    client: TestClient, admin_token: str, db_session
):
    proj = _create_project(db_session)
    resp = client.post(
        f"/api/v1/projects/{proj.id}/electronic-delivery",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.headers.get("content-type") == "application/zip"
    assert "content-disposition" in resp.headers
    disposition = resp.headers["content-disposition"]
    assert disposition.startswith("attachment")


# ─── Phase 9 P1: Real file inclusion tests ───────────────────────────────────


def test_generate_zip_with_real_file(
    client: TestClient, admin_token: str, admin_user: User, db_session
):
    """ZIP must contain actual file bytes when doc.file_path points to a real file."""
    proj = _create_project(db_session, code="REAL001", name="実ファイルテスト工事")

    # Write known content to a temp file
    pdf_content = b"%PDF-1.4 fake pdf content for testing real file inclusion"
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(pdf_content)
        tmp_path = tmp.name

    try:
        doc = Document(
            title="実ファイル図面",
            document_type=DocumentType.DRAWING,
            status=DocumentStatus.APPROVED,
            filename="real.pdf",
            file_path=tmp_path,
            file_size=len(pdf_content),
            is_pdfa=True,
            project_id=proj.id,
            owner_id=admin_user.id,
        )
        db_session.add(doc)
        db_session.commit()

        resp = client.post(
            f"/api/v1/projects/{proj.id}/electronic-delivery",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200

        zf = zipfile.ZipFile(io.BytesIO(resp.content))
        drawing_entries = [n for n in zf.namelist() if "DRAWINGS/DRAW_" in n]
        assert len(drawing_entries) == 1

        # Actual PDF bytes must be present inside the ZIP entry
        stored_bytes = zf.read(drawing_entries[0])
        assert stored_bytes == pdf_content
    finally:
        os.unlink(tmp_path)


def test_generate_zip_missing_file_fallback(
    client: TestClient, admin_token: str, admin_user: User, db_session
):
    """ZIP generation must succeed with empty placeholder when file_path is missing."""
    proj = _create_project(db_session, code="MISS001", name="欠損ファイルテスト工事")

    doc = Document(
        title="欠損ファイル図面",
        document_type=DocumentType.DRAWING,
        status=DocumentStatus.APPROVED,
        filename="missing.pdf",
        file_path="/nonexistent/path/that/does/not/exist.pdf",
        file_size=2048,
        is_pdfa=True,
        project_id=proj.id,
        owner_id=admin_user.id,
    )
    db_session.add(doc)
    db_session.commit()

    resp = client.post(
        f"/api/v1/projects/{proj.id}/electronic-delivery",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    # Must still succeed — missing file falls back to empty bytes
    assert resp.status_code == 200

    zf = zipfile.ZipFile(io.BytesIO(resp.content))
    drawing_entries = [n for n in zf.namelist() if "DRAWINGS/DRAW_" in n]
    assert len(drawing_entries) == 1

    # Fallback returns empty bytes
    stored_bytes = zf.read(drawing_entries[0])
    assert stored_bytes == b""
