"""Audit log API tests."""
from models.audit_log import AuditLog


class TestAuditLogs:
    def _create_log(self, db, action: str, resource_type: str = None, user_id: str = None):
        log = AuditLog(
            action=action,
            resource_type=resource_type,
            resource_id="resource-1",
            detail='{"key": "value"}',
            ip_address="127.0.0.1",
            user_id=user_id,
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return log

    def test_list_audit_logs_as_admin(self, client, admin_token, db_session, admin_user):
        self._create_log(db_session, "document.upload", "document", admin_user.id)
        self._create_log(db_session, "workflow.create", "workflow", admin_user.id)

        resp = client.get(
            "/api/v1/audit-logs/",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 2
        assert data["page"] == 1

    def test_list_audit_logs_forbidden_for_non_admin(self, client, viewer_token):
        resp = client.get(
            "/api/v1/audit-logs/",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert resp.status_code == 403

    def test_list_audit_logs_requires_auth(self, client):
        resp = client.get("/api/v1/audit-logs/")
        assert resp.status_code == 401

    def test_filter_by_action(self, client, admin_token, db_session, admin_user):
        self._create_log(db_session, "document.upload", "document", admin_user.id)
        self._create_log(db_session, "user.login", None, admin_user.id)

        resp = client.get(
            "/api/v1/audit-logs/?action=document.upload",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert all(item["action"] == "document.upload" for item in data["items"])

    def test_filter_by_resource_type(self, client, admin_token, db_session, admin_user):
        self._create_log(db_session, "document.upload", "document", admin_user.id)
        self._create_log(db_session, "workflow.create", "workflow", admin_user.id)

        resp = client.get(
            "/api/v1/audit-logs/?resource_type=workflow",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert all(item["resource_type"] == "workflow" for item in data["items"])

    def test_pagination(self, client, admin_token, db_session, admin_user):
        for i in range(5):
            self._create_log(db_session, f"action.{i}", "test", admin_user.id)

        resp = client.get(
            "/api/v1/audit-logs/?page=1&per_page=2",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 2
        assert data["per_page"] == 2
        assert data["pages"] >= 3

    def test_empty_audit_logs(self, client, admin_token):
        resp = client.get(
            "/api/v1/audit-logs/",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []

    def test_log_response_fields(self, client, admin_token, db_session, admin_user):
        self._create_log(db_session, "document.delete", "document", admin_user.id)

        resp = client.get(
            "/api/v1/audit-logs/",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        item = resp.json()["items"][0]
        assert "id" in item
        assert "action" in item
        assert "created_at" in item
        assert item["action"] == "document.delete"
