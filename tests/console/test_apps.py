"""Tests for the app distribution API (releases, release notes, build info, downloads).

These assert that responses reflect the real CivilPDF-Editor GitHub Release
v1.2.1 (Tauri v2, unsigned stable, text edit mode + Phase A/B/C features included).
"""

# Real asset filenames as attached to GitHub Release v1.2.1. Filenames contain
# "1.2.1" matching the version set in package.json / tauri.conf.json for this
# release. GitHub replaces spaces with dots in asset names.
# Download URLs are `{base}/{filename}`.
_BASE = "https://github.com/Kensan196948G/CivilPDF-Editor/releases/download/v1.2.1"
_REAL_FILENAMES = {
    "win-exe": "CivilPDF.Editor_1.2.1_x64-setup.exe",
    "win-msi": "CivilPDF.Editor_1.2.1_x64_en-US.msi",
    "mac-dmg": "CivilPDF.Editor_1.2.1_universal.dmg",
    "linux-deb": "CivilPDF.Editor_1.2.1_amd64.deb",
    "linux-appimage": "CivilPDF.Editor_1.2.1_amd64.AppImage",
    "linux-rpm": "CivilPDF.Editor-1.2.1-1.x86_64.rpm",
}


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class TestReleases:
    def test_releases_structure(self, client, admin_token):
        resp = client.get("/api/v1/apps/releases", headers=_auth(admin_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["stable_version"] == "v1.2.1"
        assert isinstance(data["packages"], list)
        assert isinstance(data["channels"], list)
        # Only the stable channel exists for v1.2.1.
        assert len(data["channels"]) == 1
        assert data["channels"][0]["id"] == "stable"
        assert data["channels"][0]["version"] == "v1.2.1"
        # user_count is not measured, so it is reported as 0 (no fabrication).
        assert data["channels"][0]["user_count"] == 0

    def test_releases_include_all_real_packages(self, client, admin_token):
        resp = client.get("/api/v1/apps/releases", headers=_auth(admin_token))
        ids = {p["id"] for p in resp.json()["packages"]}
        # Exactly the six real Tauri-generated assets — no fabricated zip/pkg/intune.
        assert ids == {
            "win-exe",
            "win-msi",
            "mac-dmg",
            "linux-deb",
            "linux-appimage",
            "linux-rpm",
        }

    def test_no_fabricated_packages(self, client, admin_token):
        resp = client.get("/api/v1/apps/releases", headers=_auth(admin_token))
        ids = {p["id"] for p in resp.json()["packages"]}
        # These were fabricated (Tauri does not produce them) and must be gone.
        assert {"win-zip", "mac-pkg", "ent-intune"}.isdisjoint(ids)

    def test_real_filenames_and_version(self, client, admin_token):
        resp = client.get("/api/v1/apps/releases", headers=_auth(admin_token))
        by_id = {p["id"]: p for p in resp.json()["packages"]}
        for pkg_id, filename in _REAL_FILENAMES.items():
            assert by_id[pkg_id]["filename"] == filename
            # version field reports the release version (1.2.1), not the filename fragment.
            assert by_id[pkg_id]["version"] == "1.2.1"

    def test_macos_dmg_metadata(self, client, admin_token):
        resp = client.get("/api/v1/apps/releases", headers=_auth(admin_token))
        pkg = next(p for p in resp.json()["packages"] if p["id"] == "mac-dmg")
        assert pkg["platform"] == "macos"
        assert pkg["format"] == "dmg"
        assert pkg["filename"].endswith(".dmg")

    def test_windows_msi_metadata(self, client, admin_token):
        resp = client.get("/api/v1/apps/releases", headers=_auth(admin_token))
        pkg = next(p for p in resp.json()["packages"] if p["id"] == "win-msi")
        assert pkg["platform"] == "windows"
        assert pkg["format"] == "msi"
        assert pkg["filename"].endswith(".msi")

    def test_linux_packages_present(self, client, admin_token):
        resp = client.get("/api/v1/apps/releases", headers=_auth(admin_token))
        linux = {
            p["format"] for p in resp.json()["packages"] if p["platform"] == "linux"
        }
        assert linux == {"deb", "appimage", "rpm"}

    def test_packages_unavailable_without_base_url(
        self, client, admin_token, monkeypatch
    ):
        monkeypatch.delenv("APPS_RELEASE_BASE_URL", raising=False)
        resp = client.get("/api/v1/apps/releases", headers=_auth(admin_token))
        assert all(p["available"] is False for p in resp.json()["packages"])

    def test_packages_available_with_base_url(self, client, admin_token, monkeypatch):
        monkeypatch.setenv("APPS_RELEASE_BASE_URL", _BASE)
        resp = client.get("/api/v1/apps/releases", headers=_auth(admin_token))
        assert all(p["available"] is True for p in resp.json()["packages"])

    def test_releases_requires_auth(self, client):
        resp = client.get("/api/v1/apps/releases")
        assert resp.status_code == 401


class TestReleaseNotes:
    def test_all_notes(self, client, admin_token):
        resp = client.get("/api/v1/apps/release-notes", headers=_auth(admin_token))
        assert resp.status_code == 200
        notes = resp.json()["notes"]
        assert len(notes) == 1
        first = notes[0]
        assert first["version"] == "1.2.1"
        assert first["channel"] == "stable"
        assert all("type" in i and "text" in i for i in first["items"])

    def test_notes_describe_real_features(self, client, admin_token):
        resp = client.get("/api/v1/apps/release-notes", headers=_auth(admin_token))
        texts = " ".join(i["text"] for n in resp.json()["notes"] for i in n["items"])
        # Real features: PDF viewing (M1) and electronic seal (M2).
        assert "PDF 表示" in texts
        assert "電子印鑑" in texts
        # v1.2.1 headline feature: text edit mode.
        assert "テキスト編集" in texts
        # Honest disclosure of the unsigned build limitation.
        assert "未署名" in texts

    def test_notes_have_no_fabricated_content(self, client, admin_token):
        resp = client.get("/api/v1/apps/release-notes", headers=_auth(admin_token))
        blob = resp.text
        # Fabricated items from the old fake data must not reappear.
        for fake in ("CVE-2026-1234", "Teams", "2.4.1", "2.5.0", "OCR日本語縦書き"):
            assert fake not in blob

    def test_filter_by_channel(self, client, admin_token):
        resp = client.get(
            "/api/v1/apps/release-notes",
            params={"channel": "stable"},
            headers=_auth(admin_token),
        )
        assert resp.status_code == 200
        notes = resp.json()["notes"]
        assert len(notes) == 1
        assert notes[0]["channel"] == "stable"

    def test_invalid_channel_rejected(self, client, admin_token):
        resp = client.get(
            "/api/v1/apps/release-notes",
            params={"channel": "beta"},
            headers=_auth(admin_token),
        )
        # beta is no longer a valid channel — only "stable" is accepted.
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
        assert data["stable_version"] == "v1.2.1"
        assert data["channel"] == "stable"
        assert "Tauri" in data["runtime"]
        assert isinstance(data["supported_os"], list) and data["supported_os"]
        # Linux support is declared (Tauri produces .deb/.AppImage/.rpm).
        assert any("Linux" in os_name for os_name in data["supported_os"])
        assert "min_supported_version" in data
        # build_number always present; commit/date may be None when env unset
        assert data["build_number"]

    def test_build_info_env_injection(self, client, admin_token, monkeypatch):
        # Env is read at request time, so monkeypatch alone takes effect.
        monkeypatch.setenv("APPS_BUILD_COMMIT", "abc1234")
        monkeypatch.setenv("APPS_BUILD_DATE", "2026-06-22")
        monkeypatch.setenv("APPS_BUILD_NUMBER", "1.2.1+build.42")
        resp = client.get("/api/v1/apps/build-info", headers=_auth(admin_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["git_commit"] == "abc1234"
        assert data["build_date"] == "2026-06-22"
        assert data["build_number"] == "1.2.1+build.42"

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

    def test_download_configured_returns_real_github_url(
        self, client, admin_token, monkeypatch
    ):
        monkeypatch.setenv("APPS_RELEASE_BASE_URL", _BASE)
        monkeypatch.setenv("APPS_SHA256_WIN_EXE", "deadbeef")
        resp = client.get("/api/v1/apps/download/win-exe", headers=_auth(admin_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["url"] == f"{_BASE}/{_REAL_FILENAMES['win-exe']}"
        assert data["sha256"] == "deadbeef"

    def test_download_url_for_every_package(self, client, admin_token, monkeypatch):
        monkeypatch.setenv("APPS_RELEASE_BASE_URL", _BASE)
        for pkg_id, filename in _REAL_FILENAMES.items():
            resp = client.get(
                f"/api/v1/apps/download/{pkg_id}", headers=_auth(admin_token)
            )
            assert resp.status_code == 200
            assert resp.json()["url"] == f"{_BASE}/{filename}"

    def test_download_sha256_none_when_env_unset(
        self, client, admin_token, monkeypatch
    ):
        monkeypatch.setenv("APPS_RELEASE_BASE_URL", _BASE)
        monkeypatch.delenv("APPS_SHA256_MAC_DMG", raising=False)
        resp = client.get("/api/v1/apps/download/mac-dmg", headers=_auth(admin_token))
        assert resp.status_code == 200
        # No fabricated checksum: None when the env var is not set.
        assert resp.json()["sha256"] is None

    def test_download_unknown_package_404(self, client, admin_token):
        resp = client.get(
            "/api/v1/apps/download/does-not-exist", headers=_auth(admin_token)
        )
        assert resp.status_code == 404

    def test_download_requires_auth(self, client):
        resp = client.get("/api/v1/apps/download/win-exe")
        assert resp.status_code == 401
