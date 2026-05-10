"""Document management API tests."""
import io
from unittest.mock import patch


def _make_pdf_bytes() -> bytes:
    """Minimal valid PDF bytes for testing."""
    return b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n%%EOF"


class TestDocumentUpload:
    def _create_project(self, client, admin_token) -> str:
        resp = client.post(
            "/api/v1/projects/",
            json={"name": "Doc Project", "code": "DOC-001"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        return resp.json()["id"]

    def test_upload_pdf(self, client, admin_token):
        project_id = self._create_project(client, admin_token)
        resp = client.post(
            "/api/v1/documents/",
            data={"project_id": project_id, "title": "Test Drawing", "document_type": "drawing"},
            files={"file": ("test.pdf", io.BytesIO(_make_pdf_bytes()), "application/pdf")},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Test Drawing"
        assert data["document_type"] == "drawing"
        assert data["project_id"] == project_id

    def test_upload_non_pdf_rejected(self, client, admin_token):
        project_id = self._create_project(client, admin_token)
        resp = client.post(
            "/api/v1/documents/",
            data={"project_id": project_id, "title": "Bad File"},
            files={"file": ("test.txt", io.BytesIO(b"not a pdf"), "text/plain")},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 415

    def test_list_documents_empty(self, client, admin_token):
        resp = client.get("/api/v1/documents/", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_documents_with_filter(self, client, admin_token):
        project_id = self._create_project(client, admin_token)
        client.post(
            "/api/v1/documents/",
            data={"project_id": project_id, "title": "Photo", "document_type": "photo"},
            files={"file": ("p.pdf", io.BytesIO(_make_pdf_bytes()), "application/pdf")},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        resp = client.get(
            f"/api/v1/documents/?project_id={project_id}&document_type=photo",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_get_document(self, client, admin_token):
        project_id = self._create_project(client, admin_token)
        upload = client.post(
            "/api/v1/documents/",
            data={"project_id": project_id, "title": "Get Test"},
            files={"file": ("g.pdf", io.BytesIO(_make_pdf_bytes()), "application/pdf")},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        doc_id = upload.json()["id"]
        resp = client.get(f"/api/v1/documents/{doc_id}", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        assert resp.json()["id"] == doc_id

    def test_update_document_title(self, client, admin_token):
        project_id = self._create_project(client, admin_token)
        upload = client.post(
            "/api/v1/documents/",
            data={"project_id": project_id, "title": "Old Title"},
            files={"file": ("u.pdf", io.BytesIO(_make_pdf_bytes()), "application/pdf")},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        doc_id = upload.json()["id"]
        resp = client.patch(
            f"/api/v1/documents/{doc_id}",
            json={"title": "New Title"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "New Title"

    def test_delete_document(self, client, admin_token):
        project_id = self._create_project(client, admin_token)
        upload = client.post(
            "/api/v1/documents/",
            data={"project_id": project_id, "title": "Delete Me"},
            files={"file": ("d.pdf", io.BytesIO(_make_pdf_bytes()), "application/pdf")},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        doc_id = upload.json()["id"]
        resp = client.delete(f"/api/v1/documents/{doc_id}", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 204
        get_resp = client.get(f"/api/v1/documents/{doc_id}", headers={"Authorization": f"Bearer {admin_token}"})
        assert get_resp.status_code == 404

    def test_upload_requires_auth(self, client):
        resp = client.post(
            "/api/v1/documents/",
            data={"project_id": "some-id", "title": "No Auth"},
            files={"file": ("f.pdf", io.BytesIO(_make_pdf_bytes()), "application/pdf")},
        )
        assert resp.status_code == 401

    def test_list_documents_with_status_filter(self, client, admin_token):
        project_id = self._create_project(client, admin_token)
        client.post(
            "/api/v1/documents/",
            data={"project_id": project_id, "title": "Draft Doc"},
            files={"file": ("s.pdf", io.BytesIO(_make_pdf_bytes()), "application/pdf")},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        resp = client.get(
            "/api/v1/documents/?status=draft",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_upload_file_too_large(self, client, admin_token):
        project_id = self._create_project(client, admin_token)
        # Patch MAX_FILE_BYTES to 100 bytes to avoid 100MB allocation in tests
        with patch("api.documents.MAX_FILE_BYTES", 100):
            small_but_over_limit = b"%PDF-1.4\n" + b"x" * 200
            resp = client.post(
                "/api/v1/documents/",
                data={"project_id": project_id, "title": "Too Large"},
                files={"file": ("big.pdf", io.BytesIO(small_but_over_limit), "application/pdf")},
                headers={"Authorization": f"Bearer {admin_token}"},
            )
        assert resp.status_code == 413

    def test_update_document_not_found(self, client, admin_token):
        resp = client.patch(
            "/api/v1/documents/nonexistent-id",
            json={"title": "New Title"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 404

    def test_update_document_forbidden(self, client, admin_token, viewer_token):
        project_id = self._create_project(client, admin_token)
        upload = client.post(
            "/api/v1/documents/",
            data={"project_id": project_id, "title": "Admin Doc"},
            files={"file": ("a.pdf", io.BytesIO(_make_pdf_bytes()), "application/pdf")},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        doc_id = upload.json()["id"]
        resp = client.patch(
            f"/api/v1/documents/{doc_id}",
            json={"title": "Hijacked"},
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert resp.status_code == 403

    def test_delete_document_not_found(self, client, admin_token):
        resp = client.delete(
            "/api/v1/documents/nonexistent-id",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 404

    def test_delete_document_forbidden(self, client, admin_token, viewer_token):
        project_id = self._create_project(client, admin_token)
        upload = client.post(
            "/api/v1/documents/",
            data={"project_id": project_id, "title": "Protected Doc"},
            files={"file": ("p.pdf", io.BytesIO(_make_pdf_bytes()), "application/pdf")},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        doc_id = upload.json()["id"]
        resp = client.delete(
            f"/api/v1/documents/{doc_id}",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert resp.status_code == 403
