"""End-to-end API integration tests — full user journey flows.

These tests verify complete business flows from authentication through
document management and approval workflows. Each test class represents
a distinct user scenario.
"""

import io
import uuid


def _minimal_pdf() -> bytes:
    return b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n%%EOF"


def _unique_code() -> str:
    return f"E2E-{uuid.uuid4().hex[:6].upper()}"


# ─── Helpers ──────────────────────────────────────────────────────────────────


def create_project(client, token: str, name: str = "E2E Project") -> str:
    resp = client.post(
        "/api/v1/projects/",
        json={"name": name, "code": _unique_code()},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def upload_document(
    client, token: str, project_id: str, title: str = "E2E Doc"
) -> dict:
    resp = client.post(
        "/api/v1/documents/",
        data={"project_id": project_id, "title": title},
        files={"file": ("doc.pdf", io.BytesIO(_minimal_pdf()), "application/pdf")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    return resp.json()


def create_user_and_token(
    client, admin_token: str, *, email: str, username: str, role: str = "engineer"
) -> tuple[str, str]:
    resp = client.post(
        "/api/v1/users/",
        json={
            "email": email,
            "username": username,
            "full_name": username.capitalize(),
            "password": "Test1234!",
            "role": role,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201, resp.json()
    user_id = resp.json()["id"]
    token_resp = client.post(
        "/api/v1/auth/token",
        data={"username": email, "password": "Test1234!"},
    )
    assert token_resp.status_code == 200
    return user_id, token_resp.json()["access_token"]


# ─── Tests ────────────────────────────────────────────────────────────────────


class TestAuthFlow:
    """Scenario: User authentication flows."""

    def test_login_returns_access_and_refresh_tokens(self, client, admin_user):
        resp = client.post(
            "/api/v1/auth/token",
            data={"username": "admin@example.com", "password": "Admin1234!"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "bearer"

    def test_invalid_credentials_returns_401(self, client, admin_user):
        resp = client.post(
            "/api/v1/auth/token",
            data={"username": "admin@example.com", "password": "WrongPass!"},
        )
        assert resp.status_code == 401

    def test_access_protected_endpoint_with_valid_token(self, client, admin_token):
        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["email"] == "admin@example.com"

    def test_access_protected_endpoint_without_token_returns_401(self, client):
        resp = client.get("/api/v1/documents/")
        assert resp.status_code == 401

    def test_refresh_token_issues_new_access_token(self, client, admin_user):
        login = client.post(
            "/api/v1/auth/token",
            data={"username": "admin@example.com", "password": "Admin1234!"},
        )
        refresh_token = login.json()["refresh_token"]
        resp = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert resp.status_code == 200
        assert "access_token" in resp.json()


class TestDocumentFlow:
    """Scenario: Document lifecycle — upload, list, preview, delete."""

    def test_upload_and_list_documents(self, client, admin_token):
        project_id = create_project(client, admin_token)
        doc = upload_document(client, admin_token, project_id, title="設計図 v1")

        assert doc["title"] == "設計図 v1"
        assert doc["status"] == "draft"
        assert doc["is_pdfa"] is False

        list_resp = client.get(
            "/api/v1/documents/",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert list_resp.status_code == 200
        ids = [d["id"] for d in list_resp.json()]
        assert doc["id"] in ids

    def test_delete_document_removes_it_from_list(self, client, admin_token):
        project_id = create_project(client, admin_token)
        doc = upload_document(client, admin_token, project_id)

        del_resp = client.delete(
            f"/api/v1/documents/{doc['id']}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert del_resp.status_code == 204

        list_resp = client.get(
            "/api/v1/documents/",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        ids = [d["id"] for d in list_resp.json()]
        assert doc["id"] not in ids

    def test_non_member_engineer_cannot_upload_document(self, client, admin_token):
        # Upload requires project membership (RBAC hardening).
        engineer_id, engineer_token = create_user_and_token(
            client,
            admin_token,
            email="eng@e2e.com",
            username="eng_e2e",
            role="engineer",
        )
        project_id = create_project(client, admin_token)
        resp = client.post(
            "/api/v1/documents/",
            data={"project_id": project_id, "title": "エンジニア図面"},
            files={"file": ("f.pdf", io.BytesIO(_minimal_pdf()), "application/pdf")},
            headers={"Authorization": f"Bearer {engineer_token}"},
        )
        assert resp.status_code == 404

        # After membership is granted the same user can upload.
        resp = client.post(
            f"/api/v1/projects/{project_id}/members/{engineer_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 204
        resp = client.post(
            "/api/v1/documents/",
            data={"project_id": project_id, "title": "エンジニア図面"},
            files={"file": ("f.pdf", io.BytesIO(_minimal_pdf()), "application/pdf")},
            headers={"Authorization": f"Bearer {engineer_token}"},
        )
        assert resp.status_code == 201

    def test_upload_non_pdf_returns_415(self, client, admin_token):
        project_id = create_project(client, admin_token)
        resp = client.post(
            "/api/v1/documents/",
            data={"project_id": project_id, "title": "不正ファイル"},
            files={"file": ("f.txt", io.BytesIO(b"not a pdf"), "text/plain")},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 415


class TestApprovalWorkflowFlow:
    """Scenario: Full approval workflow — create, approve, reject."""

    def test_full_approval_flow_all_steps_approved(self, client, admin_token):
        # Setup: project + doc + approver users
        project_id = create_project(client, admin_token)
        doc = upload_document(client, admin_token, project_id)

        approver1_id, approver1_token = create_user_and_token(
            client,
            admin_token,
            email="approver1@e2e.com",
            username="approver1",
            role="manager",
        )
        approver2_id, approver2_token = create_user_and_token(
            client,
            admin_token,
            email="approver2@e2e.com",
            username="approver2",
            role="manager",
        )

        # Create workflow with 2 approvers
        wf_resp = client.post(
            "/api/v1/workflows/",
            json={
                "document_id": doc["id"],
                "approver_ids": [approver1_id, approver2_id],
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert wf_resp.status_code == 201
        wf = wf_resp.json()
        assert wf["status"] == "in_progress"
        assert len(wf["steps"]) == 2

        # Approver 1 approves step 1
        step1 = next(s for s in wf["steps"] if s["order"] == 1)
        decide1 = client.post(
            f"/api/v1/workflows/{wf['id']}/steps/{step1['id']}/decide",
            json={"decision": "approve", "comment": "問題なし"},
            headers={"Authorization": f"Bearer {approver1_token}"},
        )
        assert decide1.status_code == 200
        wf_after1 = decide1.json()
        assert wf_after1["status"] == "in_progress"  # Still pending step 2

        # Approver 2 approves step 2
        step2 = next(s for s in wf["steps"] if s["order"] == 2)
        decide2 = client.post(
            f"/api/v1/workflows/{wf['id']}/steps/{step2['id']}/decide",
            json={"decision": "approve", "comment": "承認"},
            headers={"Authorization": f"Bearer {approver2_token}"},
        )
        assert decide2.status_code == 200
        wf_final = decide2.json()
        assert wf_final["status"] == "approved"

        # Document should now be approved
        doc_resp = client.get(
            f"/api/v1/documents/{doc['id']}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert doc_resp.json()["status"] == "approved"

    def test_rejection_immediately_closes_workflow(self, client, admin_token):
        project_id = create_project(client, admin_token)
        doc = upload_document(client, admin_token, project_id)

        approver_id, approver_token = create_user_and_token(
            client,
            admin_token,
            email="approver_rej@e2e.com",
            username="approver_rej",
            role="manager",
        )

        wf_resp = client.post(
            "/api/v1/workflows/",
            json={"document_id": doc["id"], "approver_ids": [approver_id]},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        wf = wf_resp.json()
        step = wf["steps"][0]

        decide = client.post(
            f"/api/v1/workflows/{wf['id']}/steps/{step['id']}/decide",
            json={"decision": "reject", "comment": "差し戻し"},
            headers={"Authorization": f"Bearer {approver_token}"},
        )
        assert decide.status_code == 200
        assert decide.json()["status"] == "rejected"

        doc_resp = client.get(
            f"/api/v1/documents/{doc['id']}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert doc_resp.json()["status"] == "rejected"

    def test_non_approver_cannot_decide_step(self, client, admin_token):
        project_id = create_project(client, admin_token)
        doc = upload_document(client, admin_token, project_id)

        approver_id, _ = create_user_and_token(
            client,
            admin_token,
            email="real_approver@e2e.com",
            username="real_approver",
            role="manager",
        )
        _, intruder_token = create_user_and_token(
            client,
            admin_token,
            email="intruder@e2e.com",
            username="intruder",
            role="manager",
        )

        wf_resp = client.post(
            "/api/v1/workflows/",
            json={"document_id": doc["id"], "approver_ids": [approver_id]},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        wf = wf_resp.json()
        step = wf["steps"][0]

        decide = client.post(
            f"/api/v1/workflows/{wf['id']}/steps/{step['id']}/decide",
            json={"decision": "approve"},
            headers={"Authorization": f"Bearer {intruder_token}"},
        )
        assert decide.status_code == 403

    def test_duplicate_workflow_for_same_document_returns_409(
        self, client, admin_token
    ):
        project_id = create_project(client, admin_token)
        doc = upload_document(client, admin_token, project_id)
        approver_id, _ = create_user_and_token(
            client,
            admin_token,
            email="dup_approver@e2e.com",
            username="dup_approver",
            role="manager",
        )

        client.post(
            "/api/v1/workflows/",
            json={"document_id": doc["id"], "approver_ids": [approver_id]},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        dup = client.post(
            "/api/v1/workflows/",
            json={"document_id": doc["id"], "approver_ids": [approver_id]},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert dup.status_code == 409


class TestGDPRPrivacyFlow:
    """Scenario: GDPR Art.17 data deletion and export flows."""

    def test_user_can_export_own_data(self, client, admin_token, admin_user):
        resp = client.get(
            f"/api/v1/privacy/users/{admin_user.id}/export",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        # DataExportResponse has flat structure: user_id, email, etc.
        assert data["email"] == "admin@example.com"
        assert data["user_id"] == admin_user.id
        assert "documents" in data

    def test_user_can_request_deletion_of_own_data(
        self, client, admin_token, admin_user
    ):
        project_id = create_project(client, admin_token)
        upload_document(client, admin_token, project_id)

        del_resp = client.delete(
            f"/api/v1/privacy/users/{admin_user.id}/data",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert del_resp.status_code == 200
        body = del_resp.json()
        assert body["user_id"] == admin_user.id
        assert "documents_marked" in body
        assert body["documents_marked"] >= 1

    def test_user_cannot_request_deletion_for_other_user(self, client, admin_token):
        _, other_token = create_user_and_token(
            client,
            admin_token,
            email="other_gdpr@e2e.com",
            username="other_gdpr",
            role="engineer",
        )
        resp = client.delete(
            f"/api/v1/privacy/users/{admin_token[:10]}/data",
            headers={"Authorization": f"Bearer {other_token}"},
        )
        # other user trying to delete admin's data → 403 or 404
        assert resp.status_code in (403, 404)


class TestRBACFlow:
    """Scenario: Role-Based Access Control enforcement across endpoints."""

    def test_admin_can_create_users(self, client, admin_token):
        resp = client.post(
            "/api/v1/users/",
            json={
                "email": "newuser@rbac.com",
                "username": "newuser_rbac",
                "full_name": "New User",
                "password": "NewUser1234!",
                "role": "engineer",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 201

    def test_viewer_cannot_create_users(self, client, admin_token):
        _, viewer_token = create_user_and_token(
            client,
            admin_token,
            email="viewer_rbac@e2e.com",
            username="viewer_rbac",
            role="viewer",
        )
        resp = client.post(
            "/api/v1/users/",
            json={
                "email": "another@rbac.com",
                "username": "another_rbac",
                "full_name": "Another",
                "password": "Another1234!",
            },
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert resp.status_code == 403

    def test_viewer_cannot_access_audit_logs(self, client, admin_token):
        _, viewer_token = create_user_and_token(
            client,
            admin_token,
            email="viewer_audit@e2e.com",
            username="viewer_audit",
            role="viewer",
        )
        resp = client.get(
            "/api/v1/audit-logs/",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert resp.status_code == 403

    def test_admin_can_access_audit_logs(self, client, admin_token):
        resp = client.get(
            "/api/v1/audit-logs/",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert "items" in resp.json()
