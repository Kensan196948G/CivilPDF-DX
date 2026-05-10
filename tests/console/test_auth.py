"""Authentication API tests."""
from models.user import User


class TestLogin:
    def test_login_success(self, client, admin_user):
        resp = client.post(
            "/api/v1/auth/token",
            data={"username": "admin@example.com", "password": "Admin1234!"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client, admin_user):
        resp = client.post(
            "/api/v1/auth/token",
            data={"username": "admin@example.com", "password": "WrongPass"},
        )
        assert resp.status_code == 401

    def test_login_unknown_email(self, client):
        resp = client.post(
            "/api/v1/auth/token",
            data={"username": "nobody@example.com", "password": "Admin1234!"},
        )
        assert resp.status_code == 401

    def test_get_me(self, client, admin_token):
        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "admin@example.com"
        assert data["role"] == "admin"

    def test_get_me_no_token(self, client):
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    def test_token_refresh(self, client, admin_user):
        login_resp = client.post(
            "/api/v1/auth/token",
            data={"username": "admin@example.com", "password": "Admin1234!"},
        )
        refresh_token = login_resp.json()["refresh_token"]
        resp = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_token_refresh_with_access_token_fails(self, client, admin_token):
        resp = client.post("/api/v1/auth/refresh", json={"refresh_token": admin_token})
        assert resp.status_code == 401

    def test_login_inactive_user(self, client, inactive_user):
        resp = client.post(
            "/api/v1/auth/token",
            data={"username": "inactive@example.com", "password": "Inactive123!"},
        )
        assert resp.status_code == 403

    def test_refresh_token_inactive_user(self, client, admin_user, db_session):
        from models.user import UserStatus
        login_resp = client.post(
            "/api/v1/auth/token",
            data={"username": "admin@example.com", "password": "Admin1234!"},
        )
        refresh_token = login_resp.json()["refresh_token"]

        # Deactivate user directly in DB after obtaining the token
        user = db_session.query(User).filter_by(email="admin@example.com").first()
        user.status = UserStatus.INACTIVE
        db_session.commit()

        resp = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert resp.status_code == 401


class TestHealthCheck:
    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
