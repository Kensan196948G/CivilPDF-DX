"""App distribution API — release channel, release notes, build info and installer downloads.

Source of truth: the public GitHub Release of CivilPDF-Editor (Tauri v2 desktop app).

    https://github.com/Kensan196948G/CivilPDF-Editor/releases/tag/v0.1.0-beta

This module intentionally avoids fabricated metadata. Values that are not measured
(e.g. active user counts) are reported honestly (0 / None) rather than guessed.
The current release is an UNSIGNED public beta whose features are limited to
M1 (PDF viewing) and M2 (electronic seal). OCR and large-format drawings are not
implemented yet.
"""

import os
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from auth.dependencies import get_current_user
from models.user import User

router = APIRouter(prefix="/apps", tags=["App Distribution"])

# Current (and only) published release. Matches the GitHub Release tag v0.1.0-beta.
_VERSION = "0.1.0-beta"
# Public release date of v0.1.0-beta (GitHub Release publication date).
_RELEASE_DATE = "2026-06-20"

Channel = Literal["beta"]
NoteType = Literal["FEAT", "FIX", "SEC", "IMP", "NOTE"]


# Env is read at request time (not import time) so deployment configuration and
# tests take effect without a module reload.
def _base_url() -> str:
    """Base URL of the GitHub Releases asset path (empty when unconfigured).

    Set in deployment to:
        https://github.com/Kensan196948G/CivilPDF-Editor/releases/download/v0.1.0-beta
    """
    return os.getenv("APPS_RELEASE_BASE_URL", "").rstrip("/")


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
    sha256: str | None = None
    message: str | None = None


class ReleaseNoteItem(BaseModel):
    type: NoteType
    text: str


class ReleaseNote(BaseModel):
    version: str
    channel: Channel
    release_date: str
    summary: str
    items: list[ReleaseNoteItem]
    highlights: str | None = None


class ReleaseNotesResponse(BaseModel):
    notes: list[ReleaseNote]


class BuildInfo(BaseModel):
    product: str
    stable_version: str
    build_number: str
    git_commit: str | None
    build_date: str | None
    channel: str
    runtime: str
    supported_os: list[str]
    min_supported_version: str


def _resolve_sha256(pkg_id: str) -> str | None:
    """Resolve a package checksum from APPS_SHA256_<PKG_ID> (e.g. APPS_SHA256_WIN_EXE).

    Returns None when unset so the frontend can omit the integrity badge. We do not
    hardcode checksums here because they are produced by the release pipeline.
    """
    key = "APPS_SHA256_" + pkg_id.upper().replace("-", "_")
    value = os.getenv(key)
    return value or None


def _pkg(
    pkg_id: str, platform: str, fmt: str, label: str, filename: str, size: str
) -> ReleasePackage:
    return ReleasePackage(
        id=pkg_id,
        platform=platform,
        format=fmt,
        label=label,
        filename=filename,
        version=_VERSION,
        size_label=size,
        sha256=_resolve_sha256(pkg_id),
        download_path=f"/api/v1/apps/download/{pkg_id}",
        available=bool(_base_url()),
    )


def _build_packages() -> list[ReleasePackage]:
    """Build the package list fresh so env-driven checksums/availability stay current.

    Filenames MUST match the real assets attached to the GitHub Release v0.1.0-beta
    (GitHub replaces spaces in asset names with dots). The download URL is then
    `{APPS_RELEASE_BASE_URL}/{filename}`.
    """
    return [
        _pkg(
            "win-exe",
            "windows",
            "exe",
            "インストーラー (.exe / NSIS)",
            "CivilPDF.Editor_0.1.0_x64-setup.exe",
            "約 1.9 MB",
        ),
        _pkg(
            "win-msi",
            "windows",
            "msi",
            "インストーラー (.msi)",
            "CivilPDF.Editor_0.1.0_x64_en-US.msi",
            "約 2.4 MB",
        ),
        _pkg(
            "mac-dmg",
            "macos",
            "dmg",
            "ディスクイメージ (.dmg / Universal)",
            "CivilPDF.Editor_0.1.0_universal.dmg",
            "約 4.5 MB",
        ),
        _pkg(
            "linux-deb",
            "linux",
            "deb",
            "Debian / Ubuntu (.deb)",
            "CivilPDF.Editor_0.1.0_amd64.deb",
            "約 2.3 MB",
        ),
        _pkg(
            "linux-appimage",
            "linux",
            "appimage",
            "AppImage (.AppImage)",
            "CivilPDF.Editor_0.1.0_amd64.AppImage",
            "約 80 MB",
        ),
        _pkg(
            "linux-rpm",
            "linux",
            "rpm",
            "Fedora / RHEL (.rpm)",
            "CivilPDF.Editor-0.1.0-1.x86_64.rpm",
            "約 2.3 MB",
        ),
    ]


# Only the beta channel exists today. user_count is 0 because we do not collect
# install telemetry — reporting a measured-looking number would be dishonest.
_CHANNELS: list[ChannelInfo] = [
    ChannelInfo(
        id="beta",
        label="Beta",
        version=f"v{_VERSION}",
        release_date=_RELEASE_DATE,
        description=(
            "公開ベータ（未署名）。機能は M1 PDF表示 + M2 電子印鑑のみ。"
            "SmartScreen / Gatekeeper の警告が表示されます。"
        ),
        user_count=0,
    ),
]


_RELEASE_NOTES: list[ReleaseNote] = [
    ReleaseNote(
        version=_VERSION,
        channel="beta",
        release_date=_RELEASE_DATE,
        summary="初回公開ベータ — PDF表示 + 電子印鑑",
        items=[
            ReleaseNoteItem(type="FEAT", text="PDF 表示（M1: ページ閲覧・ズーム）"),
            ReleaseNoteItem(
                type="FEAT",
                text="電子印鑑（M2: 印影作成・配置・PDF 埋め込み）",
            ),
            ReleaseNoteItem(
                type="NOTE",
                text="未署名ベータ。Windows SmartScreen / macOS Gatekeeper の警告あり",
            ),
            ReleaseNoteItem(
                type="NOTE",
                text="OCR・大判図面（A0/A1）対応は未実装。今後のリリースで提供予定",
            ),
        ],
        highlights=(
            "v0.1.0-beta — リリースノート\n\n"
            f"リリース日: {_RELEASE_DATE}\nチャンネル: Beta（公開ベータ・未署名）\n\n"
            "搭載機能:\n"
            "- PDF 表示（M1）: ページ閲覧・ズーム\n"
            "- 電子印鑑（M2）: 印影作成・配置・PDF への埋め込み\n\n"
            "既知の制約:\n"
            "- 未署名ビルドのため、Windows では SmartScreen、macOS では Gatekeeper の\n"
            "  警告が表示されます（実行は可能）。\n"
            "- OCR・大判図面（A0/A1）対応は本リリースには含まれません。\n\n"
            "技術スタック: Tauri v2（システムの WebView を利用）"
        ),
    ),
]


@router.get("/releases", response_model=AppsReleasesResponse)
def get_releases(_: User = Depends(get_current_user)) -> AppsReleasesResponse:
    """Return release metadata for all platforms and distribution channels."""
    return AppsReleasesResponse(
        stable_version=f"v{_VERSION}",
        packages=_build_packages(),
        channels=_CHANNELS,
    )


@router.get("/release-notes", response_model=ReleaseNotesResponse)
def get_release_notes(
    channel: Optional[Channel] = None, _: User = Depends(get_current_user)
) -> ReleaseNotesResponse:
    """Return release notes, optionally filtered by distribution channel."""
    notes = _RELEASE_NOTES
    if channel is not None:
        notes = [n for n in notes if n.channel == channel]
    return ReleaseNotesResponse(notes=notes)


@router.get("/build-info", response_model=BuildInfo)
def get_build_info(_: User = Depends(get_current_user)) -> BuildInfo:
    """Return build metadata for the currently distributed build.

    Values come from the build pipeline (APPS_BUILD_* env vars); safe defaults
    are returned when unset so the endpoint never leaks secrets or fails.
    """
    return BuildInfo(
        product="CivilPDF Editor Client",
        stable_version=f"v{_VERSION}",
        build_number=os.getenv("APPS_BUILD_NUMBER", f"{_VERSION}+local"),
        git_commit=os.getenv("APPS_BUILD_COMMIT") or None,
        build_date=os.getenv("APPS_BUILD_DATE") or None,
        channel="beta",
        runtime="Tauri v2（システムの WebView を利用・未署名ベータ）",
        supported_os=[
            "Windows 10 / 11 (64bit)",
            "macOS 13 Ventura+ (Universal)",
            "Linux (.deb / .AppImage / .rpm, x86_64)",
        ],
        min_supported_version=os.getenv("APPS_MIN_SUPPORTED_VERSION", _VERSION),
    )


@router.get("/download/{package_id}", response_model=DownloadUrlResponse)
def get_download_url(
    package_id: str, _: User = Depends(get_current_user)
) -> DownloadUrlResponse:
    """Return the download URL for a specific installer package.

    Returns url=null with a message when APPS_RELEASE_BASE_URL is not configured,
    so the frontend can show a 'coming soon' state gracefully. When configured,
    the URL is `{base}/{filename}` where filename matches the real GitHub asset.
    """
    pkg = next((p for p in _build_packages() if p.id == package_id), None)
    if pkg is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Package not found"
        )
    base = _base_url()
    if not base:
        return DownloadUrlResponse(
            url=None, sha256=pkg.sha256, message="ダウンロードリンクは近日公開予定です"
        )
    return DownloadUrlResponse(url=f"{base}/{pkg.filename}", sha256=pkg.sha256)
