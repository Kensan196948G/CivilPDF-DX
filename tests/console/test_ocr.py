"""OCR API stub tests."""
import io


def _make_pdf_bytes() -> bytes:
    return b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n%%EOF"


class TestOcrApi:
    def _create_document(self, client, admin_token) -> str:
        proj = client.post(
            "/api/v1/projects/",
            json={"name": "OCR Project", "code": "OCR-001"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        project_id = proj.json()["id"]
        doc = client.post(
            "/api/v1/documents/",
            data={"project_id": project_id, "title": "OCR Test", "document_type": "drawing"},
            files={"file": ("test.pdf", io.BytesIO(_make_pdf_bytes()), "application/pdf")},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        return doc.json()["id"]

    def test_start_ocr_job(self, client, admin_token):
        doc_id = self._create_document(client, admin_token)
        resp = client.post(
            "/api/v1/ocr/process",
            json={"document_id": doc_id},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 202
        data = resp.json()
        assert data["document_id"] == doc_id
        assert data["status"] == "queued"
        assert "job_id" in data

    def test_start_ocr_unknown_document(self, client, admin_token):
        resp = client.post(
            "/api/v1/ocr/process",
            json={"document_id": "00000000-0000-0000-0000-000000000000"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 404

    def test_get_ocr_job_status(self, client, admin_token):
        doc_id = self._create_document(client, admin_token)
        start = client.post(
            "/api/v1/ocr/process",
            json={"document_id": doc_id},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        job_id = start.json()["job_id"]
        resp = client.get(
            f"/api/v1/ocr/jobs/{job_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["job_id"] == job_id
        assert data["status"] in ("queued", "processing", "completed")

    def test_get_ocr_result_stub(self, client, admin_token):
        doc_id = self._create_document(client, admin_token)
        start = client.post(
            "/api/v1/ocr/process",
            json={"document_id": doc_id},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        job_id = start.json()["job_id"]
        resp = client.get(
            f"/api/v1/ocr/jobs/{job_id}/result",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["job_id"] == job_id
        assert isinstance(data["pages"], list)
        assert len(data["pages"]) > 0

    def test_get_unknown_job(self, client, admin_token):
        resp = client.get(
            "/api/v1/ocr/jobs/nonexistent-id",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 404

    def test_ocr_requires_auth(self, client):
        resp = client.post("/api/v1/ocr/process", json={"document_id": "x"})
        assert resp.status_code == 401
