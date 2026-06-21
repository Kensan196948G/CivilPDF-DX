"""Stats API tests."""

import io

from models.document import Document, DocumentStatus


def _pdf_bytes() -> bytes:
    return b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n%%EOF"


def _create_project(client, token, code="STAT-001", name="Stats Project") -> str:
    resp = client.post(
        "/api/v1/projects/",
        json={"name": name, "code": code},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def _upload(client, token, project_id, title="Doc", doc_type="drawing") -> str:
    resp = client.post(
        "/api/v1/documents/",
        data={"project_id": project_id, "title": title, "document_type": doc_type},
        files={"file": (f"{title}.pdf", io.BytesIO(_pdf_bytes()), "application/pdf")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def _set_status(db_session, doc_id, status: DocumentStatus) -> None:
    doc = db_session.query(Document).filter(Document.id == doc_id).first()
    doc.status = status
    db_session.add(doc)
    db_session.commit()


class TestStats:
    def test_get_stats_authenticated(self, client, admin_token):
        resp = client.get(
            "/api/v1/stats/",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "total_documents" in data
        assert "pending_approvals" in data
        assert "active_users" in data
        assert "approved_this_month" in data
        assert "uploaded_this_week" in data
        assert "total_file_size_bytes" in data
        assert "by_type" in data
        assert "by_status" in data

    def test_get_stats_unauthenticated(self, client):
        resp = client.get("/api/v1/stats/")
        assert resp.status_code == 401

    def test_get_stats_counts_are_non_negative(self, client, admin_token):
        resp = client.get(
            "/api/v1/stats/",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        data = resp.json()
        assert data["total_documents"] >= 0
        assert data["active_users"] >= 0
        assert data["total_file_size_bytes"] >= 0

    def test_by_type_uses_plain_string_keys(self, client, admin_token):
        project_id = _create_project(client, admin_token, code="STAT-TYPE")
        _upload(client, admin_token, project_id, title="Drawing1", doc_type="drawing")
        resp = client.get(
            "/api/v1/stats/",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        data = resp.json()
        # Keys must be plain enum *values* (e.g. "drawing"), not "DocumentType.DRAWING".
        assert "drawing" in data["by_type"]
        assert data["by_type"]["drawing"] == 1
        assert all("." not in k for k in data["by_type"])
        assert all("." not in k for k in data["by_status"])


class TestProjectStats:
    def test_requires_auth(self, client):
        resp = client.get("/api/v1/stats/projects")
        assert resp.status_code == 401

    def test_empty_projects(self, client, admin_token):
        resp = client.get(
            "/api/v1/stats/projects",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["period"] == 30
        assert data["items"] == []

    def test_aggregates_documents_by_status(self, client, admin_token, db_session):
        project_id = _create_project(client, admin_token, code="STAT-AGG")
        approved = _upload(client, admin_token, project_id, title="A")
        rejected = _upload(client, admin_token, project_id, title="R")
        _upload(client, admin_token, project_id, title="P")  # stays draft

        _set_status(db_session, approved, DocumentStatus.APPROVED)
        _set_status(db_session, rejected, DocumentStatus.REJECTED)

        resp = client.get(
            "/api/v1/stats/projects?period=90",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["period"] == 90
        row = next(p for p in data["items"] if p["id"] == project_id)
        assert row["total"] == 3
        assert row["ok"] == 1  # approved
        assert row["ng"] == 1  # rejected
        assert row["warn"] == 1  # draft / in-progress
        assert row["code"] == "STAT-AGG"

    def test_project_without_documents_has_zero_counts(self, client, admin_token):
        project_id = _create_project(client, admin_token, code="STAT-EMPTY")
        resp = client.get(
            "/api/v1/stats/projects",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        data = resp.json()
        row = next(p for p in data["items"] if p["id"] == project_id)
        assert row["total"] == 0
        assert row["ok"] == 0
        assert row["ng"] == 0
        assert row["warn"] == 0

    def test_invalid_period_rejected(self, client, admin_token):
        resp = client.get(
            "/api/v1/stats/projects?period=0",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 422

    def test_non_admin_does_not_see_other_projects(
        self, client, admin_token, viewer_token
    ):
        """Authorization scope: a non-admin who is not a project member must not
        see another organization's project (or its aggregates) via /stats/projects."""
        _create_project(client, admin_token, code="STAT-SCOPE", name="Scoped")
        admin_items = client.get(
            "/api/v1/stats/projects",
            headers={"Authorization": f"Bearer {admin_token}"},
        ).json()["items"]
        assert any(p["code"] == "STAT-SCOPE" for p in admin_items)

        viewer_items = client.get(
            "/api/v1/stats/projects",
            headers={"Authorization": f"Bearer {viewer_token}"},
        ).json()["items"]
        assert all(p["code"] != "STAT-SCOPE" for p in viewer_items)


class TestDailyStats:
    def test_requires_auth(self, client):
        resp = client.get("/api/v1/stats/daily")
        assert resp.status_code == 401

    def test_returns_one_entry_per_day(self, client, admin_token):
        resp = client.get(
            "/api/v1/stats/daily?period=7",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["period"] == 7
        assert len(data["series"]) == 7
        assert all("date" in p and "count" in p for p in data["series"])
        # Oldest -> newest ordering.
        dates = [p["date"] for p in data["series"]]
        assert dates == sorted(dates)

    def test_counts_recent_uploads(self, client, admin_token):
        project_id = _create_project(client, admin_token, code="STAT-DAILY")
        _upload(client, admin_token, project_id, title="Today1")
        _upload(client, admin_token, project_id, title="Today2")

        resp = client.get(
            "/api/v1/stats/daily?period=30",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        data = resp.json()
        total = sum(p["count"] for p in data["series"])
        assert total == 2
        # The two uploads land on the latest (today) bucket.
        assert data["series"][-1]["count"] == 2

    def test_invalid_period_rejected(self, client, admin_token):
        resp = client.get(
            "/api/v1/stats/daily?period=400",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 422

    def test_non_admin_daily_excludes_other_projects(
        self, client, admin_token, viewer_token
    ):
        """Authorization scope: daily upload counts for a non-admin must exclude
        documents in projects they do not belong to (no cross-tenant volume leak)."""
        project_id = _create_project(client, admin_token, code="STAT-DSCOPE")
        _upload(client, admin_token, project_id, title="X")
        _upload(client, admin_token, project_id, title="Y")

        viewer_series = client.get(
            "/api/v1/stats/daily?period=30",
            headers={"Authorization": f"Bearer {viewer_token}"},
        ).json()["series"]
        assert sum(p["count"] for p in viewer_series) == 0

        admin_series = client.get(
            "/api/v1/stats/daily?period=30",
            headers={"Authorization": f"Bearer {admin_token}"},
        ).json()["series"]
        assert sum(p["count"] for p in admin_series) >= 2
