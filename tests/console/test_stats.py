"""Stats API tests."""


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
