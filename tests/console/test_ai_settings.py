"""AI model settings API tests — admin-only CRUD and connection test."""

from unittest.mock import MagicMock, patch

import pytest
from cryptography.fernet import Fernet

from services import ai_settings as ai_settings_service


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def fernet_key(monkeypatch):
    """Inject a valid Fernet key so encrypt/decrypt work in tests."""
    key = Fernet.generate_key().decode()
    monkeypatch.setattr(ai_settings_service.settings, "m365_fernet_key", key)
    return key


# ── GET /api/v1/ai-config ─────────────────────────────────────────────────────


class TestGetAiConfig:
    def test_admin_gets_default_config(self, client, admin_token):
        resp = client.get(
            "/api/v1/ai-config",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert set(data.keys()) == {"model_name", "enabled", "has_api_key"}
        assert data["model_name"] == "claude-haiku-4-5-20251001"
        assert data["enabled"] is False
        assert data["has_api_key"] is False

    def test_non_admin_returns_403(self, client, viewer_token):
        resp = client.get(
            "/api/v1/ai-config",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert resp.status_code == 403

    def test_unauthenticated_returns_401(self, client):
        resp = client.get("/api/v1/ai-config")
        assert resp.status_code == 401


# ── PUT /api/v1/ai-config ─────────────────────────────────────────────────────


class TestUpdateAiConfig:
    def test_update_model_name_and_enabled(self, client, admin_token, fernet_key):
        resp = client.put(
            "/api/v1/ai-config",
            json={"model_name": "claude-sonnet-4-6", "enabled": True},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["model_name"] == "claude-sonnet-4-6"
        assert data["enabled"] is True
        assert data["has_api_key"] is False  # no api_key sent

    def test_update_api_key_sets_has_api_key(self, client, admin_token, fernet_key):
        resp = client.put(
            "/api/v1/ai-config",
            json={"api_key": "sk-ant-test-key"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["has_api_key"] is True

    def test_api_key_never_returned_in_response(self, client, admin_token, fernet_key):
        resp = client.put(
            "/api/v1/ai-config",
            json={"api_key": "sk-ant-supersecret"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        body_text = resp.text
        assert "sk-ant-supersecret" not in body_text

    def test_get_after_update_reflects_changes(self, client, admin_token, fernet_key):
        client.put(
            "/api/v1/ai-config",
            json={
                "model_name": "claude-haiku-4-5-20251001",
                "enabled": True,
                "api_key": "sk-ant-x",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        resp = client.get(
            "/api/v1/ai-config",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["enabled"] is True
        assert data["has_api_key"] is True

    def test_non_admin_cannot_update(self, client, viewer_token, fernet_key):
        resp = client.put(
            "/api/v1/ai-config",
            json={"model_name": "claude-sonnet-4-6"},
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert resp.status_code == 403

    def test_partial_update_preserves_other_fields(
        self, client, admin_token, fernet_key
    ):
        # Set initial state
        client.put(
            "/api/v1/ai-config",
            json={"model_name": "claude-sonnet-4-6", "enabled": True},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        # Update only enabled → model_name must remain
        resp = client.put(
            "/api/v1/ai-config",
            json={"enabled": False},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["model_name"] == "claude-sonnet-4-6"
        assert data["enabled"] is False


# ── POST /api/v1/ai-config/test ───────────────────────────────────────────────


class TestTestAiConnection:
    def test_returns_not_ok_when_no_api_key(
        self, client, admin_token, fernet_key, monkeypatch
    ):
        # Ensure no env-var fallback either
        monkeypatch.setenv("ANTHROPIC_API_KEY", "")
        monkeypatch.setattr(ai_settings_service.settings, "anthropic_api_key", "")

        resp = client.post(
            "/api/v1/ai-config/test",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is False
        assert "APIキー" in data["message"]

    def test_returns_ok_when_api_key_valid(self, client, admin_token, fernet_key):
        # Store a key in DB
        client.put(
            "/api/v1/ai-config",
            json={"api_key": "sk-ant-fake-valid"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        mock_msg = MagicMock()
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_msg

        with patch("api.ai_settings.anthropic.Anthropic", return_value=mock_client):
            resp = client.post(
                "/api/v1/ai-config/test",
                headers={"Authorization": f"Bearer {admin_token}"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert "接続成功" in data["message"]

    def test_returns_not_ok_on_anthropic_error(self, client, admin_token, fernet_key):
        # Store a key in DB
        client.put(
            "/api/v1/ai-config",
            json={"api_key": "sk-ant-bad-key"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        with patch("api.ai_settings.anthropic.Anthropic") as mock_cls:
            mock_cls.return_value.messages.create.side_effect = Exception(
                "Invalid API key"
            )
            resp = client.post(
                "/api/v1/ai-config/test",
                headers={"Authorization": f"Bearer {admin_token}"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is False
        assert "Invalid API key" in data["message"]

    def test_non_admin_cannot_test(self, client, viewer_token):
        resp = client.post(
            "/api/v1/ai-config/test",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert resp.status_code == 403
