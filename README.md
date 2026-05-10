# CivilPDF-DX

**現場が止まらないPDF管理を。**
図面の赤入れ、承認フロー、電子納品チェックまでを一気通貫でカバーする、建設業特化のオープンソースPDFプラットフォームです。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Built with Claude Code](https://img.shields.io/badge/Built%20with-Claude%20Code-blueviolet)](https://claude.ai)

---

## 概要

CivilPDF-DX は、建設・土木業における PDF 業務を統合管理するプラットフォームです。

- **GUIアプリ（Windows exe）** — PDF閲覧・編集・注釈・OCR・電子印鑑・図面赤入れ
- **管理コンソール（WebUI）** — ユーザー管理・権限管理・文書管理・承認ワークフロー・監査ログ・AI/OCR管理

## 特徴

- 🏗️ **建設業特化** — 写真台帳・是正指示書・安全書類・検査記録をテンプレートから即生成
- 📡 **オフラインファースト** — 通信環境を選ばず動作。復帰時に自動同期
- 📋 **電子納品対応** — 国交省電子納品要領準拠のPDF/A変換・構成チェック・しおり自動生成
- 🔐 **エンタープライズ認証** — Entra ID + HENNGE ONE によるSSO・MFA・デバイス制御
- 🤖 **AI支援** — 文書要約・自動分類・校正・文書名自動生成（利用ポリシー制御付き）

## アーキテクチャ

```
CivilPDF-DX/
├── src/
│   ├── app/           # GUIアプリ（Windowsデスクトップ）
│   │   ├── core/      # PDF処理エンジン
│   │   ├── ui/        # UI コンポーネント
│   │   ├── pdf/       # PDF操作（結合・分割・変換・注釈）
│   │   ├── ocr/       # OCR処理（Tesseract連携）
│   │   ├── stamps/    # 電子印鑑
│   │   ├── sync/      # オフライン同期エージェント
│   │   └── auth/      # Entra ID / HENNGE ONE 認証
│   │
│   ├── console/       # 管理コンソール（WebUI）
│   │   ├── frontend/  # React + TypeScript
│   │   └── backend/   # FastAPI + PostgreSQL
│   │
│   └── shared/        # 共通モジュール
│       ├── types/     # 型定義
│       ├── utils/     # ユーティリティ
│       └── config/    # 設定管理
│
├── docs/              # ドキュメント
├── tests/             # テスト
├── scripts/           # ビルド・デプロイスクリプト
├── assets/            # アイコン・テンプレート・印鑑画像
├── CLAUDE.md          # Claude Code プロジェクト設定
└── .claude/           # Claude Code スキル・設定
```

## 技術スタック

| レイヤー | 技術 |
|---|---|
| GUIアプリ | Electron or Tauri + TypeScript |
| フロントエンド（管理コンソール） | React + TypeScript + Tailwind CSS |
| バックエンド | FastAPI (Python) |
| データベース | PostgreSQL + Redis |
| ローカルDB | SQLite（オフライン用） |
| PDF処理 | pdf-lib, qpdf, Poppler (utilities) |
| OCR | Tesseract OCR（日本語対応） |
| PDF/A検証 | veraPDF |
| AI | Claude API |
| 認証 | Entra ID (OIDC/SAML) + HENNGE ONE |
| CI/CD | GitHub Actions |
| コードレビュー | CodeRabbit, Codex Review |

## セットアップ

### 前提条件

- Node.js >= 20.x
- Python >= 3.11
- PostgreSQL >= 15
- Redis >= 7

### インストール

```bash
# リポジトリをクローン
git clone https://github.com/<your-org>/CivilPDF-DX.git
cd CivilPDF-DX

# 依存関係のインストール（詳細は docs/guides/setup.md を参照）
# アプリ
cd src/app && npm install

# 管理コンソール フロントエンド
cd src/console/frontend && npm install

# 管理コンソール バックエンド
cd src/console/backend && pip install -r requirements.txt
```

### 開発サーバー起動

```bash
# 管理コンソール バックエンド
cd src/console/backend
uvicorn main:app --reload --port 8000

# 管理コンソール フロントエンド
cd src/console/frontend
npm run dev

# GUIアプリ（開発モード）
cd src/app
npm run dev
```

## ロードマップ

- [ ] **Phase 1（MVP）** — PDF基本操作 + 閲覧・注釈・電子印鑑 + 基本認証
- [ ] **Phase 2** — 管理コンソール + ワークフロー + 監査ログ
- [ ] **Phase 3** — OCR/AI機能 + 電子納品チェッカー + オフライン同期
- [ ] **Phase 4** — 外部連携（SharePoint/Teams/desknet's NEO）+ 高度なレポート

## コントリビューション

[CONTRIBUTING.md](CONTRIBUTING.md) をご確認ください。

## ライセンス

[MIT License](LICENSE)

## 開発体制

このプロジェクトは [Claude Code](https://claude.ai) を主開発ツールとして使用し、
[CodeRabbit](https://coderabbit.ai) および Codex Review によるAIコードレビューを導入しています。
