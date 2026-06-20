"""App distribution API — release channel management and installer download endpoints."""

import os

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from auth.dependencies import get_current_user
from models.user import User

router = APIRouter(prefix="/apps", tags=["App Distribution"])

_STABLE = "2.4.1"
_BETA = "2.5.0-beta.3"
_INSIDER = "2.5.0-alpha.9"

# Configure via environment: set to base URL of CDN / GitHub Releases asset path
_BASE = os.getenv("APPS_RELEASE_BASE_URL", "").rstrip("/")


class ReleasePackage(BaseModel):
    id: str
    platform: str
    format: str
    label: str
    filename: str
    version: str
    size_label: str
    sha256: str | None
    download_path: str
    available: bool


class ChannelInfo(BaseModel):
    id: str
    label: str
    version: str
    release_date: str
    description: str
    user_count: int


class AppsReleasesResponse(BaseModel):
    stable_version: str
    packages: list[ReleasePackage]
    channels: list[ChannelInfo]


class DownloadUrlResponse(BaseModel):
    url: str | None
    message: str | None = None


def _pkg(
    pkg_id: str, platform: str, fmt: str, label: str, filename: str, size: str
) -> ReleasePackage:
    return ReleasePackage(
        id=pkg_id,
        platform=platform,
        format=fmt,
        label=label,
        filename=filename,
        version=_STABLE,
        size_label=size,
        sha256=None,
        download_path=f"/api/v1/apps/download/{pkg_id}",
        available=bool(_BASE),
    )


_PACKAGES: list[ReleasePackage] = [
    _pkg(
        "win-exe",
        "windows",
        "exe",
        "インストーラー (.exe)",
        f"CivilPDF-Editor-Setup-{_STABLE}.exe",
        "87.4 MB",
    ),
    _pkg(
        "win-zip",
        "windows",
        "zip",
        "ポータブル (.zip)",
        f"CivilPDF-Editor-Portable-{_STABLE}.zip",
        "94.1 MB",
    ),
    _pkg(
        "mac-dmg",
        "macos",
        "dmg",
        "ディスクイメージ (.dmg)",
        f"CivilPDF-Editor-{_STABLE}.dmg",
        "82.6 MB",
    ),
    _pkg(
        "ent-intune",
        "enterprise",
        "intunewin",
        "Intune パッケージ",
        f"CivilPDF-Editor-{_STABLE}.intunewin",
        "91.2 MB",
    ),
]

_CHANNELS: list[ChannelInfo] = [
    ChannelInfo(
        id="stable",
        label="Stable",
        version=f"v{_STABLE}",
        release_date="2026-04-28",
        description="本番推奨。十分な検証済みリリース。",
        user_count=211,
    ),
    ChannelInfo(
        id="beta",
        label="Beta",
        version=f"v{_BETA}",
        release_date="2026-05-07",
        description="機能検証版。次期安定版の先行確認。",
        user_count=28,
    ),
    ChannelInfo(
        id="insider",
        label="Insider",
        version=f"v{_INSIDER}",
        release_date="2026-05-10",
        description="開発最前線。破壊的変更が含まれる可能性あり。",
        user_count=9,
    ),
]


@router.get("/releases", response_model=AppsReleasesResponse)
def get_releases(_: User = Depends(get_current_user)) -> AppsReleasesResponse:
    """Return release metadata for all platforms and distribution channels."""
    return AppsReleasesResponse(
        stable_version=f"v{_STABLE}",
        packages=_PACKAGES,
        channels=_CHANNELS,
    )


@router.get("/download/{package_id}", response_model=DownloadUrlResponse)
def get_download_url(
    package_id: str, _: User = Depends(get_current_user)
) -> DownloadUrlResponse:
    """Return the download URL for a specific installer package.

    Returns url=null with a message when APPS_RELEASE_BASE_URL is not configured,
    so the frontend can show a 'coming soon' state gracefully.
    """
    pkg = next((p for p in _PACKAGES if p.id == package_id), None)
    if pkg is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Package not found"
        )
    if not _BASE:
        return DownloadUrlResponse(
            url=None, message="ダウンロードリンクは近日公開予定です"
        )
    return DownloadUrlResponse(url=f"{_BASE}/{pkg.filename}")
