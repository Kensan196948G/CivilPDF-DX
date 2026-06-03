"""Tests for Organization CRUD API (Phase 8 P2 — Multi-tenancy)."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src/console/backend"))

from fastapi.testclient import TestClient

from models.organization import Organization, OrgType
from models.user import User, UserRole, UserStatus


def _create_org(
    db, name: str, code: str, org_type=OrgType.HEADQUARTERS, parent=None
) -> Organization:
    org = Organization(
        name=name,
        code=code,
        org_type=org_type,
        parent_id=parent.id if parent else None,
        path="/" if parent is None else parent.path.rstrip("/") + f"/{parent.id}",
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


# ─── Create ───────────────────────────────────────────────────────────────────


def test_create_organization_admin(client: TestClient, admin_token: str):
    resp = client.post(
        "/api/v1/organizations/",
        json={"name": "本社", "code": "HQ", "org_type": "headquarters"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "本社"
    assert data["code"] == "HQ"
    assert data["org_type"] == "headquarters"
    assert data["path"] == "/"
    assert data["is_active"] is True
    assert data["parent_id"] is None
    assert data["children"] == []


def test_create_organization_with_parent(
    client: TestClient, admin_token: str, db_session
):
    hq = _create_org(db_session, "本社", "HQ", OrgType.HEADQUARTERS)

    resp = client.post(
        "/api/v1/organizations/",
        json={
            "name": "東京支店",
            "code": "BRANCH-TKY",
            "org_type": "branch",
            "parent_id": hq.id,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["parent_id"] == hq.id
    assert hq.id in data["path"]


def test_create_organization_duplicate_code_conflict(
    client: TestClient, admin_token: str, db_session
):
    _create_org(db_session, "本社", "HQ")

    resp = client.post(
        "/api/v1/organizations/",
        json={"name": "別の本社", "code": "HQ", "org_type": "headquarters"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 409


def test_create_organization_invalid_parent_404(client: TestClient, admin_token: str):
    resp = client.post(
        "/api/v1/organizations/",
        json={
            "name": "支店",
            "code": "BR1",
            "org_type": "branch",
            "parent_id": "nonexistent-id",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404


def test_create_organization_non_admin_forbidden(client: TestClient, viewer_token: str):
    resp = client.post(
        "/api/v1/organizations/",
        json={"name": "本社", "code": "HQ", "org_type": "headquarters"},
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert resp.status_code == 403


# ─── Read ─────────────────────────────────────────────────────────────────────


def test_list_organizations(client: TestClient, admin_token: str, db_session):
    _create_org(db_session, "本社", "HQ")
    _create_org(db_session, "大阪支店", "BRANCH-OSK", OrgType.BRANCH)

    resp = client.get(
        "/api/v1/organizations/",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_list_organizations_excludes_inactive(
    client: TestClient, admin_token: str, db_session
):
    hq = _create_org(db_session, "本社", "HQ")
    hq.is_active = False
    db_session.commit()

    resp = client.get(
        "/api/v1/organizations/",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_organization(client: TestClient, admin_token: str, db_session):
    hq = _create_org(db_session, "本社", "HQ")

    resp = client.get(
        f"/api/v1/organizations/{hq.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == hq.id


def test_get_organization_not_found(client: TestClient, admin_token: str):
    resp = client.get(
        "/api/v1/organizations/nonexistent",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404


def test_organization_tree(client: TestClient, admin_token: str, db_session):
    hq = _create_org(db_session, "本社", "HQ", OrgType.HEADQUARTERS)
    _create_org(db_session, "東京支店", "BRANCH-TKY", OrgType.BRANCH, parent=hq)

    resp = client.get(
        "/api/v1/organizations/tree",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    roots = resp.json()
    assert len(roots) == 1
    assert roots[0]["code"] == "HQ"
    assert len(roots[0]["children"]) == 1
    assert roots[0]["children"][0]["code"] == "BRANCH-TKY"


# ─── Update ───────────────────────────────────────────────────────────────────


def test_update_organization_name(client: TestClient, admin_token: str, db_session):
    hq = _create_org(db_session, "本社", "HQ")

    resp = client.patch(
        f"/api/v1/organizations/{hq.id}",
        json={"name": "本社（更新）"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "本社（更新）"


def test_update_organization_non_admin_forbidden(
    client: TestClient, viewer_token: str, db_session
):
    hq = _create_org(db_session, "本社", "HQ")

    resp = client.patch(
        f"/api/v1/organizations/{hq.id}",
        json={"name": "不正更新"},
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert resp.status_code == 403


# ─── Delete (soft) ────────────────────────────────────────────────────────────


def test_delete_organization_soft(client: TestClient, admin_token: str, db_session):
    hq = _create_org(db_session, "本社", "HQ")

    resp = client.delete(
        f"/api/v1/organizations/{hq.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 204

    db_session.refresh(hq)
    assert hq.is_active is False


def test_delete_organization_with_active_children_conflict(
    client: TestClient, admin_token: str, db_session
):
    hq = _create_org(db_session, "本社", "HQ", OrgType.HEADQUARTERS)
    _create_org(db_session, "東京支店", "BRANCH-TKY", OrgType.BRANCH, parent=hq)

    resp = client.delete(
        f"/api/v1/organizations/{hq.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 409


def test_delete_organization_not_found(client: TestClient, admin_token: str):
    resp = client.delete(
        "/api/v1/organizations/nonexistent",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404


def test_delete_organization_non_admin_forbidden(
    client: TestClient, viewer_token: str, db_session
):
    hq = _create_org(db_session, "本社", "HQ")

    resp = client.delete(
        f"/api/v1/organizations/{hq.id}",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert resp.status_code == 403


# ─── Members ──────────────────────────────────────────────────────────────────


def test_list_members_direct(client: TestClient, admin_token: str, db_session):
    hq = _create_org(db_session, "本社", "HQ")
    user = User(
        email="worker@example.com",
        username="worker1",
        full_name="Worker One",
        hashed_password="x",
        role=UserRole.ENGINEER,
        status=UserStatus.ACTIVE,
        organization_id=hq.id,
    )
    db_session.add(user)
    db_session.commit()

    resp = client.get(
        f"/api/v1/organizations/{hq.id}/members",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["email"] == "worker@example.com"


def test_list_members_subtree(client: TestClient, admin_token: str, db_session):
    hq = _create_org(db_session, "本社", "HQ", OrgType.HEADQUARTERS)
    branch = _create_org(
        db_session, "東京支店", "BRANCH-TKY", OrgType.BRANCH, parent=hq
    )

    user_hq = User(
        email="hq_worker@example.com",
        username="hq1",
        full_name="HQ Worker",
        hashed_password="x",
        role=UserRole.ENGINEER,
        status=UserStatus.ACTIVE,
        organization_id=hq.id,
    )
    user_br = User(
        email="branch_worker@example.com",
        username="br1",
        full_name="Branch Worker",
        hashed_password="x",
        role=UserRole.ENGINEER,
        status=UserStatus.ACTIVE,
        organization_id=branch.id,
    )
    db_session.add_all([user_hq, user_br])
    db_session.commit()

    resp = client.get(
        f"/api/v1/organizations/{hq.id}/members?include_subtree=true",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    emails = {m["email"] for m in resp.json()}
    assert "hq_worker@example.com" in emails
    assert "branch_worker@example.com" in emails


def test_list_members_org_not_found(client: TestClient, admin_token: str):
    resp = client.get(
        "/api/v1/organizations/nonexistent/members",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404
