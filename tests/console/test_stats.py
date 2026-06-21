"""Stats API tests."""

from models.audit_log import AuditLog


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


class TestSecurityStats:
    def _log(self, db, action: str, user_id: str = None):
        log = AuditLog(
            action=action,
            resource_type="auth",
            detail="{}",
            ip_address="127.0.0.1",
            user_id=user_id,
        )
        db.add(log)
        db.commit()
        return log

    def test_security_stats_requires_auth(self, client):
        resp = client.get("/api/v1/stats/security")
        assert resp.status_code == 401

    def test_security_stats_shape(self, client, admin_token):
        resp = client.get(
            "/api/v1/stats/security",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        for key in (
            "total_events",
            "login_success_total",
            "login_failed_total",
            "login_failed_30d",
            "provision_events_total",
            "active_sessions",
        ):
            assert key in data
            assert data[key] >= 0

    def test_security_stats_counts_real_audit_events(
        self, client, admin_token, db_session, admin_user
    ):
        self._log(db_session, "m365_login_success", admin_user.id)
        self._log(db_session, "m365_login_failed", admin_user.id)
        self._log(db_session, "m365_login_failed", admin_user.id)
        self._log(db_session, "m365_user_not_found")
        self._log(db_session, "m365_user_provisioned", admin_user.id)

        resp = client.get(
            "/api/v1/stats/security",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        data = resp.json()
        assert data["login_success_total"] == 1
        # m365_login_failed (x2) + m365_user_not_found (x1) all count as failures
        assert data["login_failed_total"] == 3
        assert data["login_failed_30d"] == 3
        assert data["provision_events_total"] == 1
        assert data["total_events"] >= 5
        # admin_user is active -> at least 1 active session
        assert data["active_sessions"] >= 1

    def test_security_stats_empty(self, client, admin_token):
        resp = client.get(
            "/api/v1/stats/security",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        data = resp.json()
        assert data["login_success_total"] == 0
        assert data["login_failed_total"] == 0
        assert data["provision_events_total"] == 0


class TestSecurityConfig:
    def test_security_config_requires_auth(self, client):
        resp = client.get("/api/v1/stats/security-config")
        assert resp.status_code == 401

    def test_security_config_returns_real_settings(self, client, admin_token):
        resp = client.get(
            "/api/v1/stats/security-config",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        # Real config.py values
        assert data["access_token_expire_minutes"] >= 1
        assert data["refresh_token_expire_days"] >= 1
        assert data["jwt_algorithm"]
        assert data["max_file_size_mb"] >= 1
        # Real RBAC roles from the UserRole enum
        assert set(data["rbac_roles"]) == {
            "admin",
            "manager",
            "engineer",
            "viewer",
        }
        # Audit hash chain is implemented
        assert data["audit_chain_enabled"] is True
        assert data["audit_hash_algorithm"] == "SHA-256"
