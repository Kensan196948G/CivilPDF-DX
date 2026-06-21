"""Revision management API tests — TDD先行.

Feature #2: PDF 改訂管理 (改訂番号付きバージョン管理)
"""

import io

from models.document import Document, DocumentStatus
from models.user import Project


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_project(db, code="REV-PROJ-001"):
    proj = Project(name="改訂テストプロジェクト", code=code)
    db.add(proj)
    db.commit()
    db.refresh(proj)
    return proj


def _make_document(db, owner_id, project_id):
    doc = Document(
        title="設計図面 Rev.A",
        filename="design_rev_a.pdf",
        file_size=2048,
        project_id=project_id,
        owner_id=owner_id,
        status=DocumentStatus.DRAFT,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def _pdf_bytes():
    """Minimal PDF stub for upload tests."""
    return b"%PDF-1.4\n%%EOF"


# ── POST /api/v1/documents/{doc_id}/revisions ─────────────────────────────────


class TestUploadRevision:
    def test_manager_can_upload_revision(
        self, client, manager_token, admin_user, db_session
    ):
        proj = _make_project(db_session)
        doc = _make_document(db_session, admin_user.id, proj.id)

        resp = client.post(
            f"/api/v1/documents/{doc.id}/revisions",
            data={"revision": "B", "revision_note": "第2改訂"},
            files={
                "file": (
                    "design_rev_b.pdf",
                    io.BytesIO(_pdf_bytes()),
                    "application/pdf",
                )
            },
            headers={"Authorization": f"Bearer {manager_token}"},
        )
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert data["revision"] == "B"
        assert data["revision_note"] == "第2改訂"

    def test_upload_creates_document_version_record(
        self, client, manager_token, admin_user, db_session
    ):
        proj = _make_project(db_session, "REV-PROJ-002")
        doc = _make_document(db_session, admin_user.id, proj.id)

        client.post(
            f"/api/v1/documents/{doc.id}/revisions",
            data={"revision": "A", "revision_note": "初版"},
            files={"file": ("rev_a.pdf", io.BytesIO(_pdf_bytes()), "application/pdf")},
            headers={"Authorization": f"Bearer {manager_token}"},
        )
        resp = client.get(
            f"/api/v1/documents/{doc.id}/revisions",
            headers={"Authorization": f"Bearer {manager_token}"},
        )
        assert resp.status_code == 200
        versions = resp.json()
        assert len(versions) >= 1
        assert versions[0]["revision"] == "A"

    def test_upload_sets_is_from_editor_flag(
        self, client, manager_token, admin_user, db_session
    ):
        proj = _make_project(db_session, "REV-PROJ-003")
        doc = _make_document(db_session, admin_user.id, proj.id)

        resp = client.post(
            f"/api/v1/documents/{doc.id}/revisions",
            data={
                "revision": "C",
                "revision_note": "Editor 経由",
                "is_from_editor": "true",
            },
            files={"file": ("rev_c.pdf", io.BytesIO(_pdf_bytes()), "application/pdf")},
            headers={"Authorization": f"Bearer {manager_token}"},
        )
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert data.get("is_from_editor") is True

    def test_viewer_cannot_upload_revision(
        self, client, viewer_token, admin_user, db_session
    ):
        proj = _make_project(db_session, "REV-PROJ-004")
        doc = _make_document(db_session, admin_user.id, proj.id)

        resp = client.post(
            f"/api/v1/documents/{doc.id}/revisions",
            data={"revision": "B"},
            files={"file": ("rev_b.pdf", io.BytesIO(_pdf_bytes()), "application/pdf")},
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert resp.status_code == 403

    def test_unauthenticated_returns_401(self, client, admin_user, db_session):
        proj = _make_project(db_session, "REV-PROJ-005")
        doc = _make_document(db_session, admin_user.id, proj.id)

        resp = client.post(
            f"/api/v1/documents/{doc.id}/revisions",
            data={"revision": "B"},
            files={"file": ("rev_b.pdf", io.BytesIO(_pdf_bytes()), "application/pdf")},
        )
        assert resp.status_code == 401


# ── GET /api/v1/documents/{doc_id}/revisions ──────────────────────────────────


class TestListRevisions:
    def test_admin_can_list_revisions(
        self, client, admin_token, admin_user, db_session
    ):
        proj = _make_project(db_session, "REV-PROJ-010")
        doc = _make_document(db_session, admin_user.id, proj.id)

        resp = client.get(
            f"/api/v1/documents/{doc.id}/revisions",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_list_is_empty_when_no_revisions(
        self, client, admin_token, admin_user, db_session
    ):
        proj = _make_project(db_session, "REV-PROJ-011")
        doc = _make_document(db_session, admin_user.id, proj.id)

        resp = client.get(
            f"/api/v1/documents/{doc.id}/revisions",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json() == []

    def test_revisions_ordered_by_version_number(
        self, client, manager_token, admin_user, db_session
    ):
        proj = _make_project(db_session, "REV-PROJ-012")
        doc = _make_document(db_session, admin_user.id, proj.id)

        for rev in ("A", "B"):
            client.post(
                f"/api/v1/documents/{doc.id}/revisions",
                data={"revision": rev},
                files={
                    "file": (
                        f"rev_{rev}.pdf",
                        io.BytesIO(_pdf_bytes()),
                        "application/pdf",
                    )
                },
                headers={"Authorization": f"Bearer {manager_token}"},
            )
        resp = client.get(
            f"/api/v1/documents/{doc.id}/revisions",
            headers={"Authorization": f"Bearer {manager_token}"},
        )
        assert resp.status_code == 200
        versions = resp.json()
        assert len(versions) == 2
        nums = [v["version_number"] for v in versions]
        assert nums == sorted(nums)

    def test_unauthenticated_returns_401(self, client, admin_user, db_session):
        proj = _make_project(db_session, "REV-PROJ-013")
        doc = _make_document(db_session, admin_user.id, proj.id)

        resp = client.get(f"/api/v1/documents/{doc.id}/revisions")
        assert resp.status_code == 401

    def test_nonexistent_document_returns_404(self, client, admin_token):
        resp = client.get(
            "/api/v1/documents/no-such-doc/revisions",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 404
