"""Project management API tests."""


class TestProjectCRUD:
    def test_create_project(self, client, admin_token):
        resp = client.post(
            "/api/v1/projects/",
            json={"name": "Test Project", "code": "PRJ-001", "description": "A test project"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Test Project"
        assert data["code"] == "PRJ-001"
        assert data["is_active"] is True

    def test_create_duplicate_code(self, client, admin_token):
        payload = {"name": "Project A", "code": "DUP-001"}
        client.post("/api/v1/projects/", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        resp = client.post("/api/v1/projects/", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 409

    def test_list_projects(self, client, admin_token):
        resp = client.get("/api/v1/projects/", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_project(self, client, admin_token):
        create_resp = client.post(
            "/api/v1/projects/",
            json={"name": "Get Test", "code": "GET-001"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        project_id = create_resp.json()["id"]
        resp = client.get(f"/api/v1/projects/{project_id}", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        assert resp.json()["id"] == project_id

    def test_get_nonexistent_project(self, client, admin_token):
        resp = client.get(
            "/api/v1/projects/00000000-0000-0000-0000-000000000000",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 404

    def test_create_project_requires_auth(self, client):
        resp = client.post("/api/v1/projects/", json={"name": "No Auth", "code": "NA-001"})
        assert resp.status_code == 401
