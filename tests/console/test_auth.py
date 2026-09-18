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
        resp = client.post(
            "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
        )
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

        resp = client.post(
            "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
        )
        assert resp.status_code == 401


class TestProfileUpdate:
    def test_update_full_name(self, client, admin_token):
        resp = client.patch(
            "/api/v1/auth/me",
            json={"full_name": "Updated Name"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["full_name"] == "Updated Name"

    def test_update_full_name_empty_rejected(self, client, admin_token):
        resp = client.patch(
            "/api/v1/auth/me",
            json={"full_name": "   "},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 422

    def test_update_profile_unauthenticated(self, client):
        resp = client.patch("/api/v1/auth/me", json={"full_name": "Hacker"})
        assert resp.status_code == 401


class TestPasswordChange:
    def test_change_password_success(self, client, admin_token):
        resp = client.post(
            "/api/v1/auth/me/password",
            json={"current_password": "Admin1234!", "new_password": "NewPass5678!"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 204

    def test_change_password_wrong_current(self, client, admin_token):
        resp = client.post(
            "/api/v1/auth/me/password",
            json={"current_password": "WrongPass!", "new_password": "NewPass5678!"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 400

    def test_change_password_too_short(self, client, admin_token):
        resp = client.post(
            "/api/v1/auth/me/password",
            json={"current_password": "Admin1234!", "new_password": "short"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 422

    def test_change_password_unauthenticated(self, client):
        resp = client.post(
            "/api/v1/auth/me/password",
            json={"current_password": "Admin1234!", "new_password": "NewPass5678!"},
        )
        assert resp.status_code == 401


class TestHealthCheck:
    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestMvpAuthBypass:
    """MVP 公開デモ用のログイン認証バイパス (AUTH_BYPASS)。

    既定は無効で、明示的に有効化した環境でのみトークン無しの
    リクエストがデモ用管理ユーザーとして通る。
    """

    def test_bypass_is_off_by_default(self, client):
        from config import settings

        assert settings.auth_bypass is False
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    def test_bypass_allows_anonymous_when_enabled(self, client, monkeypatch):
        from config import settings

        monkeypatch.setattr(settings, "auth_bypass", True)
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 200
        data = resp.json()
        # The public MVP demo is internet-reachable, so the bypass user must
        # be a read-only VIEWER, never an admin — see dependencies.py
        # _get_or_create_mvp_viewer_user.
        assert data["role"] == "viewer"
        assert data["email"] == "mvp-demo@civildx.local"

    def test_bypass_user_cannot_reach_admin_endpoints(self, client, monkeypatch):
        """バイパス有効でも、匿名ユーザーは管理者専用APIへ到達できない。"""
        from config import settings

        monkeypatch.setattr(settings, "auth_bypass", True)
        resp = client.get("/api/v1/users")
        assert resp.status_code == 403

    def test_debug_bypass_is_independent_of_auth_bypass(self, client, monkeypatch):
        """DEBUG バイパスは従来通り admin のまま(開発体験を維持)。"""
        from config import settings

        monkeypatch.setattr(settings, "debug", True)
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 200
        data = resp.json()
        assert data["role"] == "admin"
        assert data["email"] == "dev@civildx.local"

    def test_both_bypasses_enabled_prefers_viewer(self, client, monkeypatch):
        """DEBUGとAUTH_BYPASSが両方有効な誤設定でも、より権限の弱いVIEWER側が勝つ。"""
        from config import settings

        monkeypatch.setattr(settings, "debug", True)
        monkeypatch.setattr(settings, "auth_bypass", True)
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 200
        data = resp.json()
        assert data["role"] == "viewer"
        assert data["email"] == "mvp-demo@civildx.local"

    def test_bypass_does_not_weaken_invalid_tokens(self, client, monkeypatch):
        """バイパス有効でも、壊れたトークンを送ってきた場合は拒否する。"""
        from config import settings

        monkeypatch.setattr(settings, "auth_bypass", True)
        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer not-a-real-token"},
        )
        assert resp.status_code == 401
