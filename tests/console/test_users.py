"""User management API tests."""


class TestUserCRUD:
    def test_create_user(self, client, admin_token):
        resp = client.post(
            "/api/v1/users/",
            json={
                "email": "engineer@example.com",
                "username": "engineer1",
                "full_name": "Test Engineer",
                "password": "Engineer123!",
                "role": "engineer",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "engineer@example.com"
        assert data["role"] == "engineer"
        assert "hashed_password" not in data

    def test_create_duplicate_email(self, client, admin_token):
        payload = {
            "email": "dup@example.com",
            "username": "dup1",
            "full_name": "Dup User",
            "password": "Dup12345!",
        }
        client.post("/api/v1/users/", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        resp = client.post("/api/v1/users/", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 409

    def test_create_user_weak_password(self, client, admin_token):
        resp = client.post(
            "/api/v1/users/",
            json={
                "email": "weak@example.com",
                "username": "weak1",
                "full_name": "Weak Pass",
                "password": "short",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 422

    def test_list_users(self, client, admin_token):
        resp = client.get(
            "/api/v1/users/",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_list_users_requires_admin(self, client, admin_token):
        client.post(
            "/api/v1/users/",
            json={
                "email": "viewer@example.com",
                "username": "viewer1",
                "full_name": "Viewer",
                "password": "Viewer123!",
                "role": "viewer",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        viewer_resp = client.post(
            "/api/v1/auth/token",
            data={"username": "viewer@example.com", "password": "Viewer123!"},
        )
        viewer_token = viewer_resp.json()["access_token"]
        resp = client.get("/api/v1/users/", headers={"Authorization": f"Bearer {viewer_token}"})
        assert resp.status_code == 403

    def test_delete_self_forbidden(self, client, admin_user, admin_token):
        resp = client.delete(
            f"/api/v1/users/{admin_user.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 400
