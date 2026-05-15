"""POST /api/v1/auth/m365/login — non-interactive M365 bridge endpoint tests.

Mocks `services.m365.lookup_user` so Graph is never actually called. Verifies:
- HTTP status mapping for every error class
- Auto-provisioning + role default
- AuditLog rows created on every branch (success / failure / provision)
- JWT issuance only when the local account is allowed to log in
"""

import pytest
from cryptography.fernet import Fernet

from services import m365 as m365_service
from models.user import User, UserRole, UserStatus
from models.audit_log import AuditLog
from models.m365_setting import M365Setting


# --- helpers ----------------------------------------------------------------


def _set_m365_settings(
    db_session,
    *,
    enabled: bool = True,
    auto_provision: bool = True,
    default_role: str = "viewer",
    has_secret: bool = True,
):
    """Materialize the singleton m365_settings row for tests.

    The auth endpoint calls get_settings_row(db) but never reads
    tenant_id/client_id/secret directly when lookup_user is mocked, so we just
    need flag fields. has_secret=True ensures the public shape would advertise
    a configured tenant if anyone introspected it.
    """
    row = db_session.query(M365Setting).filter(M365Setting.id == 1).first()
    if row is None:
        row = M365Setting(id=1)
        db_session.add(row)
    row.enabled = enabled
    row.auto_provision = auto_provision
    row.default_role = default_role
    row.tenant_id = "tid"
    row.client_id = "cid"
    row.client_secret_enc = "ciphertext" if has_secret else ""
    db_session.commit()
    db_session.refresh(row)
    return row


def _make_graph_user(
    *,
    user_id: str = "graph-id-001",
    display_name: str = "M365 User",
    email: str = "m365user@example.com",
    enabled: bool = True,
) -> dict:
    return {
        "id": user_id,
        "display_name": display_name,
        "user_principal_name": email,
        "mail": email,
        "account_enabled": enabled,
    }


@pytest.fixture
def fernet_key(monkeypatch):
    key = Fernet.generate_key().decode()
    monkeypatch.setattr(m365_service.settings, "m365_fernet_key", key)
    return key


@pytest.fixture
def mock_lookup_ok(monkeypatch):
    """Returns a setter — call it to install a fake Graph response."""
    def _install(graph_user: dict | None = None):
        graph_user = graph_user or _make_graph_user()
        monkeypatch.setattr(
            m365_service, "lookup_user", lambda db, email: graph_user
        )
        return graph_user
    return _install


# --- T1: M365 disabled → 503 ------------------------------------------------


class TestM365Disabled:
    def test_login_when_m365_disabled_returns_503(self, client, db_session, monkeypatch):
        """No mocking — _require_enabled raises M365ConfigError."""
        # Default singleton row has enabled=False
        resp = client.post(
            "/api/v1/auth/m365/login",
            json={"email": "alice@example.com"},
        )
        assert resp.status_code == 503

        log = (
            db_session.query(AuditLog)
            .filter(AuditLog.action == "m365_login_failed")
            .first()
        )
        assert log is not None
        assert "config_error" in (log.detail or "")


# --- T2: Graph 404 → 401 + audit `m365_user_not_found` ---------------------


class TestGraphUserNotFound:
    def test_returns_401_and_audits_not_found(
        self, client, db_session, monkeypatch, fernet_key
    ):
        _set_m365_settings(db_session, enabled=True)

        def _raise_not_found(db, email):
            raise m365_service.M365UserNotFound(email)

        monkeypatch.setattr(m365_service, "lookup_user", _raise_not_found)

        resp = client.post(
            "/api/v1/auth/m365/login",
            json={"email": "ghost@example.com"},
        )
        assert resp.status_code == 401

        log = (
            db_session.query(AuditLog)
            .filter(AuditLog.action == "m365_user_not_found")
            .first()
        )
        assert log is not None
        assert "ghost@example.com" in (log.detail or "")


# --- T3: account_enabled=False → 403 ---------------------------------------


class TestAccountDisabledOnGraph:
    def test_returns_403_when_graph_reports_disabled(
        self, client, db_session, fernet_key, mock_lookup_ok
    ):
        _set_m365_settings(db_session, enabled=True, auto_provision=True)
        mock_lookup_ok(_make_graph_user(email="disabled@example.com", enabled=False))

        resp = client.post(
            "/api/v1/auth/m365/login",
            json={"email": "disabled@example.com"},
        )
        assert resp.status_code == 403

        log = (
            db_session.query(AuditLog)
            .filter(AuditLog.action == "m365_login_failed")
            .filter(AuditLog.detail.like("%account_disabled%"))
            .first()
        )
        assert log is not None


# --- T4: auto_provision=True + no local user → create + JWT ----------------


class TestAutoProvision:
    def test_auto_provisions_viewer_and_returns_jwt(
        self, client, db_session, fernet_key, mock_lookup_ok
    ):
        _set_m365_settings(
            db_session, enabled=True, auto_provision=True, default_role="viewer"
        )
        graph_user = mock_lookup_ok(
            _make_graph_user(
                user_id="graph-abc",
                display_name="New M365 User",
                email="newuser@example.com",
            )
        )

        resp = client.post(
            "/api/v1/auth/m365/login",
            json={"email": "newuser@example.com"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body and body["access_token"]
        assert "refresh_token" in body and body["refresh_token"]

        # User was created with role=viewer
        user = db_session.query(User).filter(User.email == "newuser@example.com").first()
        assert user is not None
        assert user.role == UserRole.VIEWER
        assert user.status == UserStatus.ACTIVE
        assert user.entra_id == graph_user["id"]
        assert user.last_login is not None

        # Provision and login_success both audited
        provisioned = (
            db_session.query(AuditLog)
            .filter(AuditLog.action == "m365_user_provisioned")
            .first()
        )
        assert provisioned is not None
        assert provisioned.user_id == user.id

        success = (
            db_session.query(AuditLog)
            .filter(AuditLog.action == "m365_login_success")
            .first()
        )
        assert success is not None
        assert success.user_id == user.id

    def test_auto_provision_respects_default_role_override(
        self, client, db_session, fernet_key, mock_lookup_ok
    ):
        _set_m365_settings(
            db_session, enabled=True, auto_provision=True, default_role="engineer"
        )
        mock_lookup_ok(_make_graph_user(email="eng@example.com"))

        resp = client.post(
            "/api/v1/auth/m365/login", json={"email": "eng@example.com"}
        )
        assert resp.status_code == 200

        user = db_session.query(User).filter(User.email == "eng@example.com").first()
        assert user is not None
        assert user.role == UserRole.ENGINEER


# --- T5: auto_provision=False + no local user → 403 ------------------------


class TestAutoProvisionDisabled:
    def test_no_local_user_with_auto_provision_off_returns_403(
        self, client, db_session, fernet_key, mock_lookup_ok
    ):
        _set_m365_settings(db_session, enabled=True, auto_provision=False)
        mock_lookup_ok(_make_graph_user(email="stranger@example.com"))

        resp = client.post(
            "/api/v1/auth/m365/login", json={"email": "stranger@example.com"}
        )
        assert resp.status_code == 403

        # No user row created
        assert (
            db_session.query(User).filter(User.email == "stranger@example.com").first()
            is None
        )

        # Audited with the specific reason
        log = (
            db_session.query(AuditLog)
            .filter(AuditLog.action == "m365_login_failed")
            .filter(AuditLog.detail.like("%no_local_user%"))
            .first()
        )
        assert log is not None


# --- T6: existing inactive user → 403 --------------------------------------


class TestExistingInactiveUser:
    def test_inactive_local_user_cannot_login_via_m365(
        self, client, db_session, fernet_key, mock_lookup_ok, inactive_user
    ):
        _set_m365_settings(db_session, enabled=True, auto_provision=True)
        mock_lookup_ok(_make_graph_user(email=inactive_user.email))

        resp = client.post(
            "/api/v1/auth/m365/login", json={"email": inactive_user.email}
        )
        assert resp.status_code == 403

        log = (
            db_session.query(AuditLog)
            .filter(AuditLog.action == "m365_login_failed")
            .filter(AuditLog.detail.like("%local_account_not_active%"))
            .first()
        )
        assert log is not None
        assert log.user_id == inactive_user.id


# --- T7: existing active user → JWT + last_login + audit -------------------


class TestExistingActiveUser:
    def test_active_local_user_logs_in_and_backfills_entra_id(
        self, client, db_session, fernet_key, mock_lookup_ok, viewer_user
    ):
        _set_m365_settings(db_session, enabled=True, auto_provision=True)
        mock_lookup_ok(
            _make_graph_user(user_id="graph-xyz", email=viewer_user.email)
        )

        assert viewer_user.entra_id is None  # precondition

        resp = client.post(
            "/api/v1/auth/m365/login", json={"email": viewer_user.email}
        )
        assert resp.status_code == 200
        assert "access_token" in resp.json()

        db_session.expire_all()
        refreshed = db_session.query(User).filter(User.id == viewer_user.id).first()
        assert refreshed.entra_id == "graph-xyz"  # backfilled
        assert refreshed.last_login is not None

        success = (
            db_session.query(AuditLog)
            .filter(AuditLog.action == "m365_login_success")
            .filter(AuditLog.user_id == viewer_user.id)
            .first()
        )
        assert success is not None


# --- T8: Graph rejects credentials (401/403) → 502 ------------------------


class TestGraphAuthError:
    def test_graph_auth_error_returns_502(
        self, client, db_session, monkeypatch, fernet_key
    ):
        _set_m365_settings(db_session, enabled=True)

        def _raise_auth(db, email):
            raise m365_service.M365AuthError("Graph rejected the request: HTTP 401")

        monkeypatch.setattr(m365_service, "lookup_user", _raise_auth)

        resp = client.post(
            "/api/v1/auth/m365/login", json={"email": "alice@example.com"}
        )
        assert resp.status_code == 502

        log = (
            db_session.query(AuditLog)
            .filter(AuditLog.action == "m365_login_failed")
            .filter(AuditLog.detail.like("%auth_error%"))
            .first()
        )
        assert log is not None


# --- Input validation ------------------------------------------------------


class TestInputValidation:
    def test_invalid_email_returns_422(self, client):
        resp = client.post(
            "/api/v1/auth/m365/login", json={"email": "not-an-email"}
        )
        assert resp.status_code == 422

    def test_missing_email_returns_422(self, client):
        resp = client.post("/api/v1/auth/m365/login", json={})
        assert resp.status_code == 422
