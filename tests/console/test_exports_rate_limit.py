"""CSV export endpoints (RBAC + CSV-injection hardening) and auth rate limiting."""

import io

import pytest
from fastapi import Request

from main import app
from middleware.rate_limit import RateLimitMiddleware, _client_ip, reset_all
from config import settings


def _make_pdf_bytes() -> bytes:
    return b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n%%EOF"


def _create_project(client, token: str, name: str = "Export Project") -> str:
    resp = client.post(
        "/api/v1/projects/",
        json={"name": name, "code": f"EXP-{abs(hash(name)) % 100000}"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def _upload_doc(client, token: str, project_id: str, title: str = "図面") -> str:
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


def _reset_rate_limiter() -> None:
    reset_all()


@pytest.fixture(autouse=True)
def _clean_rate_limits():
    reset_all()
    yield
    reset_all()


class TestRateLimitMiddleware:
    def test_allows_up_to_limit_then_blocks(self):
        now = [100.0]
        limiter = RateLimitMiddleware(app, clock=lambda: now[0])
        for _ in range(10):
            allowed, _ = limiter._check("1.2.3.4", "/api/v1/auth/token")
            assert allowed
        allowed, retry_after = limiter._check("1.2.3.4", "/api/v1/auth/token")
        assert not allowed
        assert retry_after > 0

    def test_window_slides_forward(self):
        now = [100.0]
        limiter = RateLimitMiddleware(app, clock=lambda: now[0])
        for _ in range(10):
            limiter._check("1.2.3.4", "/api/v1/auth/token")
        now[0] = 161.0
        allowed, _ = limiter._check("1.2.3.4", "/api/v1/auth/token")
        assert allowed

    def test_unlisted_path_is_not_limited(self):
        now = [100.0]
        limiter = RateLimitMiddleware(app, clock=lambda: now[0])
        for _ in range(100):
            allowed, _ = limiter._check("1.2.3.4", "/api/v1/users/")
            assert allowed

    def test_client_ip_ignores_forwarded_header_by_default(self):
        scope = {
            "type": "http",
            "headers": [(b"x-forwarded-for", b"6.6.6.6")],
            "client": ("1.2.3.4", 1234),
        }
        assert _client_ip(Request(scope)) == "1.2.3.4"

    def test_client_ip_trusts_forwarded_header_when_enabled(self, monkeypatch):
        monkeypatch.setattr(settings, "trust_proxy_headers", True)
        scope = {
            "type": "http",
            "headers": [(b"x-forwarded-for", b"6.6.6.6")],
            "client": ("1.2.3.4", 1234),
        }
        assert _client_ip(Request(scope)) == "6.6.6.6"


class TestAuthRateLimitIntegration:
    def test_token_endpoint_returns_429_after_limit(
        self, client, admin_user, monkeypatch
    ):
        monkeypatch.setattr("api.auth.verify_password", lambda _p, _h: False)
        statuses = [
            client.post(
                "/api/v1/auth/token",
                data={"username": "admin@example.com", "password": "wrong"},
            ).status_code
            for _ in range(12)
        ]
        assert statuses.count(429) == 2
        assert statuses.count(401) == 5


class TestAuditCsvExport:
    def test_admin_export_escapes_formula_and_audits(
        self, client, admin_token, db_session
    ):
        from services.audit_chain_service import create_chained_audit_log

        create_chained_audit_log(
            db_session,
            user_id=None,
            action="test.formula",
            detail="=cmd()|calc",
            ip_address="203.0.113.10",
        )
        resp = client.get(
            "/api/v1/audit-logs/export.csv",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/csv")
        assert "attachment" in resp.headers["content-disposition"]
        text = resp.content.decode("utf-8-sig")
        assert "'=cmd()|calc" in text
        from models.audit_log import AuditLog

        exported = (
            db_session.query(AuditLog).filter(AuditLog.action == "audit.exported").all()
        )
        assert len(exported) == 1

    def test_viewer_cannot_export(self, client, viewer_token):
        resp = client.get(
            "/api/v1/audit-logs/export.csv",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert resp.status_code == 403


class TestDocumentCsvExport:
    def test_export_respects_rbac_and_escapes_formula(
        self, client, admin_token, viewer_token
    ):
        project_id = _create_project(client, admin_token)
        _upload_doc(client, admin_token, project_id, "=2+5")

        admin_resp = client.get(
            "/api/v1/documents/export.csv",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert admin_resp.status_code == 200
        assert "attachment" in admin_resp.headers["content-disposition"]
        assert "'=2+5" in admin_resp.content.decode("utf-8-sig")

        viewer_resp = client.get(
            "/api/v1/documents/export.csv",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert viewer_resp.status_code == 200
        viewer_text = viewer_resp.content.decode("utf-8-sig")
        assert "=2+5" not in viewer_text
        assert viewer_text.count("\r\n") == 1  # header row only
