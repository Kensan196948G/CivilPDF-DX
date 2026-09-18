"""Health endpoints — liveness vs database-aware readiness.

Regression context (2026-09-18): the production PostgreSQL credential stopped
authenticating around 2026-08-29. ``/health`` only reported that the process was
alive, so production served HTTP 500 for every database-backed request for three
weeks while the operational health check stayed green. ``/health/ready`` exists
so that a database outage is observable.
"""

from fastapi.testclient import TestClient

from main import app


class TestLiveness:
    def test_health_does_not_require_database(self, client):
        """Liveness must stay cheap: it reports the process, not dependencies."""
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["app"] == "CivilPDF-DX"

    def test_liveness_succeeds_even_when_the_database_is_broken(
        self, client, monkeypatch
    ):
        import main

        class _Boom:
            def connect(self):
                raise RuntimeError("database down")

        monkeypatch.setattr(main, "engine", _Boom())
        assert client.get("/health").status_code == 200


class TestReadiness:
    def test_ready_returns_200_when_database_answers(self, client):
        resp = client.get("/health/ready")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["database"] == "sqlite"
        assert body["latency_ms"] >= 0

    def test_ready_returns_503_when_database_is_unreachable(self, monkeypatch):
        import main

        class _Boom:
            def connect(self):
                raise RuntimeError("password authentication failed")

        monkeypatch.setattr(main, "engine", _Boom())
        resp = TestClient(app, raise_server_exceptions=False).get("/health/ready")
        assert resp.status_code == 503
        assert resp.json()["detail"] == "database unavailable"

    def test_ready_is_not_swallowed_by_the_audit_or_security_middleware(self, client):
        """The probe must not require authentication or emit an auth challenge."""
        resp = client.get("/health/ready")
        assert resp.status_code != 401
        assert resp.status_code != 403
