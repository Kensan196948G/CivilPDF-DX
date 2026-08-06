"""Tests for AuditMiddleware user attribution."""

import logging


class TestAuditMiddlewareUserAttribution:
    def test_mutating_request_records_authenticated_user_id(
        self, client, admin_user, admin_token, caplog
    ):
        caplog.set_level(logging.INFO, logger="audit")
        resp = client.post(
            "/api/v1/projects/",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"name": "Audit Middleware Test", "code": "AUDIT-MW-1"},
        )
        assert resp.status_code == 201

        calls = [r for r in caplog.records if r.name == "audit"]
        assert calls, "audit middleware must emit an api_call log"
        assert any(
            '"user_id": "%s"' % admin_user.id in r.getMessage() for r in calls
        ), "log must include the authenticated user id"

    def test_mutating_request_without_token_records_null_user(self, client, caplog):
        caplog.set_level(logging.INFO, logger="audit")
        resp = client.post("/api/v1/projects/", json={"name": "x", "code": "X-1"})
        assert resp.status_code == 401

        calls = [r for r in caplog.records if r.name == "audit"]
        assert calls, "audit middleware must emit an api_call log"
        assert any('"user_id": null' in r.getMessage() for r in calls)
