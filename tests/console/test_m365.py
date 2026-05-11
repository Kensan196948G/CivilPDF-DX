"""M365 integration API tests."""


class TestM365Config:
    def test_get_config_admin(self, client, admin_token):
        resp = client.get(
            "/api/v1/m365/config",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "tenant_id" in data
        assert "client_id" in data
        assert "enabled" in data

    def test_get_config_unauthenticated(self, client):
        resp = client.get("/api/v1/m365/config")
        assert resp.status_code == 401

    def test_get_config_non_admin(self, client, viewer_token):
        resp = client.get(
            "/api/v1/m365/config",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert resp.status_code == 403

    def test_update_config(self, client, admin_token):
        resp = client.put(
            "/api/v1/m365/config",
            json={"tenant_id": "test-tenant", "client_id": "test-client", "enabled": False},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["tenant_id"] == "test-tenant"
        assert data["client_id"] == "test-client"

    def test_lookup_user_disabled(self, client, admin_token):
        # M365 is disabled by default in tests
        resp = client.get(
            "/api/v1/m365/users/lookup?email=test@example.com",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 503
