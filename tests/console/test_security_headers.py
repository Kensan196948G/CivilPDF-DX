"""Tests for the security headers middleware."""


class TestSecurityHeaders:
    def test_health_response_has_security_headers(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.headers["x-content-type-options"] == "nosniff"
        assert resp.headers["x-frame-options"] == "DENY"
        assert resp.headers["referrer-policy"] == "no-referrer"
        assert "default-src 'self'" in resp.headers["content-security-policy"]
        assert "frame-ancestors 'none'" in resp.headers["content-security-policy"]
        assert "camera=()" in resp.headers["permissions-policy"]

    def test_hsts_emitted_for_https_forwarded_requests(self, client):
        resp = client.get("/health", headers={"X-Forwarded-Proto": "https"})
        assert resp.status_code == 200
        assert "strict-transport-security" in resp.headers

    def test_api_401_response_also_has_security_headers(self, client):
        resp = client.get("/api/v1/stats/")
        assert resp.status_code == 401
        assert resp.headers["x-content-type-options"] == "nosniff"
