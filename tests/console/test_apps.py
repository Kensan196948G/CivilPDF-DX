"""Tests for the app distribution API (releases, release notes, build info, downloads)."""


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class TestReleases:
    def test_releases_structure(self, client, admin_token):
        resp = client.get("/api/v1/apps/releases", headers=_auth(admin_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["stable_version"] == "v2.4.1"
        assert isinstance(data["packages"], list)
        assert isinstance(data["channels"], list)
        assert len(data["channels"]) == 3

    def test_releases_include_all_packages(self, client, admin_token):
        resp = client.get("/api/v1/apps/releases", headers=_auth(admin_token))
        ids = {p["id"] for p in resp.json()["packages"]}
        # windows exe/msi/zip, macos dmg/pkg, enterprise intune
        assert {
            "win-exe",
            "win-msi",
            "win-zip",
            "mac-dmg",
            "mac-pkg",
            "ent-intune",
        } <= ids

    def test_macos_pkg_metadata(self, client, admin_token):
        resp = client.get("/api/v1/apps/releases", headers=_auth(admin_token))
        pkg = next(p for p in resp.json()["packages"] if p["id"] == "mac-pkg")
        assert pkg["platform"] == "macos"
        assert pkg["format"] == "pkg"

    def test_windows_msi_metadata(self, client, admin_token):
        resp = client.get("/api/v1/apps/releases", headers=_auth(admin_token))
        pkg = next(p for p in resp.json()["packages"] if p["id"] == "win-msi")
        assert pkg["platform"] == "windows"
        assert pkg["format"] == "msi"
        assert pkg["filename"].endswith(".msi")

    def test_releases_requires_auth(self, client):
        resp = client.get("/api/v1/apps/releases")
        assert resp.status_code == 401


class TestReleaseNotes:
    def test_all_notes(self, client, admin_token):
        resp = client.get("/api/v1/apps/release-notes", headers=_auth(admin_token))
        assert resp.status_code == 200
        notes = resp.json()["notes"]
        assert len(notes) == 3
        first = notes[0]
        assert first["version"] == "2.4.1"
        assert first["channel"] == "stable"
        assert all("type" in i and "text" in i for i in first["items"])

    def test_filter_by_channel(self, client, admin_token):
        resp = client.get(
            "/api/v1/apps/release-notes",
            params={"channel": "beta"},
            headers=_auth(admin_token),
        )
        assert resp.status_code == 200
        notes = resp.json()["notes"]
        assert len(notes) == 1
        assert notes[0]["channel"] == "beta"

    def test_invalid_channel_rejected(self, client, admin_token):
        resp = client.get(
            "/api/v1/apps/release-notes",
            params={"channel": "nope"},
            headers=_auth(admin_token),
        )
        assert resp.status_code == 422

    def test_requires_auth(self, client):
        resp = client.get("/api/v1/apps/release-notes")
        assert resp.status_code == 401


class TestBuildInfo:
    def test_build_info_shape(self, client, admin_token):
        resp = client.get("/api/v1/apps/build-info", headers=_auth(admin_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["product"] == "CivilPDF Editor Client"
        assert data["stable_version"] == "v2.4.1"
        assert data["channel"] == "stable"
        assert isinstance(data["supported_os"], list) and data["supported_os"]
        assert "min_supported_version" in data
        # build_number always present; commit/date may be None when env unset
        assert data["build_number"]

    def test_build_info_env_injection(self, client, admin_token, monkeypatch):
        # Env is read at request time, so monkeypatch alone takes effect.
        monkeypatch.setenv("APPS_BUILD_COMMIT", "abc1234")
        monkeypatch.setenv("APPS_BUILD_DATE", "2026-06-20")
        monkeypatch.setenv("APPS_BUILD_NUMBER", "2.4.1+build.999")
        resp = client.get("/api/v1/apps/build-info", headers=_auth(admin_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["git_commit"] == "abc1234"
        assert data["build_date"] == "2026-06-20"
        assert data["build_number"] == "2.4.1+build.999"

    def test_requires_auth(self, client):
        resp = client.get("/api/v1/apps/build-info")
        assert resp.status_code == 401


class TestDownload:
    def test_download_not_configured_returns_null(
        self, client, admin_token, monkeypatch
    ):
        monkeypatch.delenv("APPS_RELEASE_BASE_URL", raising=False)
        resp = client.get("/api/v1/apps/download/win-exe", headers=_auth(admin_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["url"] is None
        assert data["message"]

    def test_download_configured_returns_url_and_checksum(
        self, client, admin_token, monkeypatch
    ):
        monkeypatch.setenv("APPS_RELEASE_BASE_URL", "https://cdn.example.com/dl/")
        monkeypatch.setenv("APPS_SHA256_WIN_EXE", "deadbeef")
        resp = client.get("/api/v1/apps/download/win-exe", headers=_auth(admin_token))
        assert resp.status_code == 200
        data = resp.json()
        assert (
            data["url"] == "https://cdn.example.com/dl/CivilPDF-Editor-Setup-2.4.1.exe"
        )
        assert data["sha256"] == "deadbeef"

    def test_download_unknown_package_404(self, client, admin_token):
        resp = client.get(
            "/api/v1/apps/download/does-not-exist", headers=_auth(admin_token)
        )
        assert resp.status_code == 404

    def test_download_requires_auth(self, client):
        resp = client.get("/api/v1/apps/download/win-exe")
        assert resp.status_code == 401
