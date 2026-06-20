"""App distribution API — release channel, release notes, build info and installer downloads."""

import os
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from auth.dependencies import get_current_user
from models.user import User

router = APIRouter(prefix="/apps", tags=["App Distribution"])

_STABLE = "2.4.1"
_BETA = "2.5.0-beta.3"
_INSIDER = "2.5.0-alpha.9"

Channel = Literal["stable", "beta", "insider"]
NoteType = Literal["FEAT", "FIX", "SEC", "IMP"]


# Env is read at request time (not import time) so deployment configuration and
# tests take effect without a module reload.
def _base_url() -> str:
    """Base URL of the CDN / GitHub Releases asset path (empty when unconfigured)."""
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

    Returns None when unset so the frontend can omit the integrity badge.
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
        version=_STABLE,
        size_label=size,
        sha256=_resolve_sha256(pkg_id),
        download_path=f"/api/v1/apps/download/{pkg_id}",
        available=bool(_base_url()),
    )


def _build_packages() -> list[ReleasePackage]:
    """Build the package list fresh so env-driven checksums/availability stay current."""
    return [
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
            "mac-pkg",
            "macos",
            "pkg",
            "インストーラー (.pkg)",
            f"CivilPDF-Editor-{_STABLE}.pkg",
            "84.0 MB",
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


_RELEASE_NOTES: list[ReleaseNote] = [
    ReleaseNote(
        version="2.4.1",
        channel="stable",
        release_date="2026-04-28",
        summary="PDF/A変換精度向上・セキュリティ修正",
        items=[
            ReleaseNoteItem(
                type="FIX", text="PDF/A-1b変換時のフォント埋め込みエラーを修正"
            ),
            ReleaseNoteItem(type="SEC", text="XSS脆弱性 (CVE-2026-1234) を修正"),
            ReleaseNoteItem(
                type="IMP", text="A0/A1大判図面のレンダリング速度を40%改善"
            ),
        ],
        highlights=(
            "v2.4.1 — リリースノート\n\nリリース日: 2026-04-28\nチャンネル: Stable\n\n"
            "変更内容:\n- PDF/A-1b変換時のフォント埋め込みエラーを修正\n"
            "- XSS脆弱性 (CVE-2026-1234) を修正\n- A0/A1大判図面のレンダリング速度を40%改善\n\n"
            "影響範囲: 全ユーザー（即時適用推奨）"
        ),
    ),
    ReleaseNote(
        version="2.5.0-beta.3",
        channel="beta",
        release_date="2026-05-07",
        summary="Teams連携・新承認フロー",
        items=[
            ReleaseNoteItem(type="FEAT", text="Microsoft Teams通知連携を追加"),
            ReleaseNoteItem(type="FEAT", text="承認フロー画面をリデザイン"),
            ReleaseNoteItem(type="FIX", text="OCR日本語縦書き認識精度を改善"),
        ],
        highlights=(
            "v2.5.0-beta.3 — リリースノート\n\nリリース日: 2026-05-07\nチャンネル: Beta\n\n"
            "変更内容:\n- Microsoft Teams通知連携を追加\n- 承認フロー画面をリデザイン（多段承認の可視化）\n"
            "- OCR日本語縦書き認識精度を改善\n\nBeta参加者のフィードバックをお願いします。"
        ),
    ),
    ReleaseNote(
        version="2.5.0-alpha.9",
        channel="insider",
        release_date="2026-05-10",
        summary="AI文書分類・PDF生成エンジン刷新",
        items=[
            ReleaseNoteItem(
                type="FEAT", text="Claude API連携による文書自動分類（実験的）"
            ),
            ReleaseNoteItem(type="FEAT", text="PDF生成エンジンをpdf-lib v2に更新"),
            ReleaseNoteItem(type="IMP", text="メモリ使用量を30%削減（大判図面）"),
        ],
        highlights=(
            "v2.5.0-alpha.9 — リリースノート\n\nリリース日: 2026-05-10\nチャンネル: Insider\n\n"
            "変更内容:\n- Claude API連携による文書自動分類（実験的機能）\n"
            "- PDF生成エンジンをpdf-lib v2に更新\n- メモリ使用量を30%削減（A0/A1大判図面）\n\n"
            "警告: 本番利用不可。フィードバック歓迎。"
        ),
    ),
]


@router.get("/releases", response_model=AppsReleasesResponse)
def get_releases(_: User = Depends(get_current_user)) -> AppsReleasesResponse:
    """Return release metadata for all platforms and distribution channels."""
    return AppsReleasesResponse(
        stable_version=f"v{_STABLE}",
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
    """Return build metadata for the currently distributed stable build.

    Values come from the build pipeline (APPS_BUILD_* env vars); safe defaults
    are returned when unset so the endpoint never leaks secrets or fails.
    """
    return BuildInfo(
        product="CivilPDF Editor Client",
        stable_version=f"v{_STABLE}",
        build_number=os.getenv("APPS_BUILD_NUMBER", f"{_STABLE}+local"),
        git_commit=os.getenv("APPS_BUILD_COMMIT") or None,
        build_date=os.getenv("APPS_BUILD_DATE") or None,
        channel="stable",
        runtime=".NET 8.0 Runtime",
        supported_os=["Windows 10 / 11 (64bit)", "macOS 13 Ventura+ (Universal)"],
        min_supported_version=os.getenv("APPS_MIN_SUPPORTED_VERSION", "2.3.0"),
    )


@router.get("/download/{package_id}", response_model=DownloadUrlResponse)
def get_download_url(
    package_id: str, _: User = Depends(get_current_user)
) -> DownloadUrlResponse:
    """Return the download URL for a specific installer package.

    Returns url=null with a message when APPS_RELEASE_BASE_URL is not configured,
    so the frontend can show a 'coming soon' state gracefully.
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
