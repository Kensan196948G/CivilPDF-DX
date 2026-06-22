"""Download endpoint — PDF Info docId embedding for Editor sync (🅐 方式).

The DX download embeds /CivilPdfDxDocId into the PDF Info dict so the
CivilPDF-Editor can read it back and target the right document when syncing a
ReviewSidecar. A pypdf-readable PDF is required (the minimal byte stub used
elsewhere would hit the raw-file fallback).
"""

import io

from pypdf import PdfReader, PdfWriter


def _valid_pdf_bytes() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def _create_doc(client, admin_token) -> str:
    pid = client.post(
        "/api/v1/projects/",
        json={"name": "DL Project", "code": "DL-001"},
        headers={"Authorization": f"Bearer {admin_token}"},
    ).json()["id"]
    resp = client.post(
        "/api/v1/documents/",
        data={"project_id": pid, "title": "DLDoc", "document_type": "other"},
        files={
            "file": ("v.pdf", io.BytesIO(_valid_pdf_bytes()), "application/pdf"),
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


class TestDownloadDocIdEmbed:
    def test_download_embeds_dx_doc_id(self, client, admin_token):
        doc_id = _create_doc(client, admin_token)
        resp = client.get(
            f"/api/v1/documents/{doc_id}/download",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        reader = PdfReader(io.BytesIO(resp.content))
        assert reader.metadata is not None
        # The Editor reads this exact key to target the right DX document.
        assert reader.metadata.get("/CivilPdfDxDocId") == doc_id

    def test_download_preserves_pdf_readability(self, client, admin_token):
        doc_id = _create_doc(client, admin_token)
        resp = client.get(
            f"/api/v1/documents/{doc_id}/download",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        # The embedded PDF must still be a valid, openable document.
        reader = PdfReader(io.BytesIO(resp.content))
        assert len(reader.pages) >= 1

    def test_download_requires_auth(self, client):
        resp = client.get("/api/v1/documents/some-id/download")
        assert resp.status_code == 401

    def test_download_unknown_document_404(self, client, admin_token):
        resp = client.get(
            "/api/v1/documents/nonexistent/download",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 404
