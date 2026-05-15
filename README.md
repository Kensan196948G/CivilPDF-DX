# CivilPDF-DX

**現場が止まらないPDF管理を。**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/Kensan196948G/CivilPDF-DX/actions/workflows/ci.yml/badge.svg)](https://github.com/Kensan196948G/CivilPDF-DX/actions/workflows/ci.yml)
[![Built with Claude Code](https://img.shields.io/badge/Built%20with-Claude%20Code-blueviolet)](https://claude.ai)

---

## 何を作るか

CivilPDF-DX は **建設・土木業務に特化したオープンソース PDF プラットフォーム**です。  
図面の赤入れ・承認フロー・電子納品チェック・OCR・AI検索を一気通貫でカバーします。

2つのモジュールで構成されます：

| モジュール | 形態 | 主な機能 |
|---|---|---|
| **GUIアプリ** | Windows デスクトップ exe | PDF 閲覧・編集・注釈・OCR・電子印鑑・図面比較・AI検索 |
| **管理コンソール** | Web ブラウザ（React） | ユーザー管理・文書管理・承認ワークフロー・監査ログ |

## 誰向けか

| 対象 | 役割 | 使い方 |
|---|---|---|
| **現場エンジニア** | 図面・施工記録の作成・赤入れ | GUI アプリ |
| **現場監督** | 承認・押印・指示書発行 | GUI アプリ + WebUI |
| **管理者・PMO** | プロジェクト管理・ユーザー権限 | 管理コンソール WebUI |
| **品質管理担当** | 電子納品チェック・監査 | 管理コンソール WebUI |

主なターゲット規模：**中堅〜大手ゼネコン・サブコン（従業員 50〜5,000 名）**

## なぜ必要か

建設業の PDF 業務には根深い課題があります：

- 📂 **属人化した紙・PDF 管理** — 図面バージョンが現場・事務所・本社でバラバラ
- 🔄 **承認フローの非効率** — 押印のためだけに出社・郵送が発生
- 📋 **電子納品の煩雑さ** — 国交省要領準拠チェックが手動で属人的
- 🔍 **検索不能な PDF 群** — 手書き・スキャン PDF はテキスト検索できない
- 🔒 **セキュリティ統制の欠如** — 誰がどの図面を閲覧したか追跡できない

CivilPDF-DX はこれらをソフトウェアで解決し、**建設現場のペーパーレス化・DX 推進**を支援します。

---

## 概要

CivilPDF-DX は、建設・土木業における PDF 業務を統合管理するプラットフォームです。

| モジュール | 説明 | 状態 |
|---|---|---|
| 管理コンソール（WebUI） | ユーザー管理・文書管理・プロジェクト管理・承認ワークフロー・監査ログ・統計・M365 統合 | ✅ Phase 4 完成 |
| GUIアプリ（Windows exe） | PDF閲覧・編集・注釈・OCR・電子印鑑・図面赤入れ | 📋 計画中 |

---

## 管理コンソール MVP 機能

| 機能 | 詳細 | 状態 |
|---|---|---|
| 🔐 JWT 認証 | ログイン / ログアウト / トークン自動更新 | ✅ |
| 👥 ユーザー管理 | CRUD・ロールベースアクセス（admin / manager / engineer / viewer） | ✅ |
| 📁 プロジェクト管理 | 作成・一覧・削除・ステータス管理 | ✅ |
| 📄 文書管理 | PDF アップロード（最大 50MB）・一覧・削除・種別分類・ダウンロード | ✅ |
| 👁 PDF プレビュー | ブラウザ内 iframe で PDF 表示（Blob URL・JWT 保護・Escape / × クローズ） | ✅ |
| ✅ 承認ワークフロー | 多段階承認（ステップ単位の承認 / 却下 / コメント） | ✅ |
| 📊 ダッシュボード統計 | 文書数・承認待ち・アクティブユーザー・月次承認数をリアルタイム集計 | ✅ |
| 🔍 監査ログ | 全操作の監査証跡（閲覧・DL・署名・拒否）、フィルタ・検索対応 | ✅ |
| ⚙️ M365 統合設定 | Azure AD テナント設定・ユーザールックアップ（管理者専用） | ✅ |
| 🔒 監査ミドルウェア | 全書き込み操作を自動ロギング（method / path / status / 実行時間 / IP） | ✅ |

---

## ドキュメント

| 文書 | リンク | 内容 |
|---|---|---|
| 要件定義書 | [docs/requirements.md](docs/requirements.md) | 機能要件・非機能要件・セキュリティ・AI・PDF処理・受け入れ基準 |
| DB設計書 | [docs/database-design.md](docs/database-design.md) | ER図・テーブル定義・インデックス・マイグレーション方針 |
| システム構成図 | [docs/architecture/system-architecture.md](docs/architecture/system-architecture.md) | 全体構成・認証フロー・デプロイ構成 |
| GUI画面一覧 | [docs/gui-screens.md](docs/gui-screens.md) | Windowsデスクトップアプリ 10画面仕様 |
| WebUI画面一覧 | [docs/webui-screens.md](docs/webui-screens.md) | 管理コンソール 11画面仕様（MVP 6画面 + 計画中 5画面） |
| フォント一覧 | [docs/civilpdf-font-docs/fonts-README.md](docs/civilpdf-font-docs/fonts-README.md) | 3層16書体・ダウンロード手順 |
| API リファレンス | [docs/api/README.md](docs/api/README.md) | REST エンドポイント一覧 |

---

## アーキテクチャ

```
CivilPDF-DX/
├── src/
│   ├── console/               # 管理コンソール（MVP）
│   │   ├── frontend/          # React 19 + TypeScript + Vite 6
│   │   │   └── src/
│   │   │       ├── api/       # axios クライアント + 各ドメイン API
│   │   │       │   ├── stats.ts      # 📊 ダッシュボード統計
│   │   │       │   ├── auditLogs.ts  # 🔍 監査ログ
│   │   │       │   ├── workflows.ts  # ✅ 承認ワークフロー
│   │   │       │   └── ...           # auth / users / documents / projects
│   │   │       ├── components/
│   │   │       │   └── enterprise/views/  # 11 画面 (Dashboard / Workflow / Audit / ...)
│   │   │       └── store/     # zustand auth store
│   │   └── backend/           # FastAPI + SQLAlchemy 2.0 + PostgreSQL
│   │       ├── api/           # REST エンドポイント
│   │       │   ├── auth.py        # 🔐 JWT 認証
│   │       │   ├── users.py       # 👥 ユーザー管理
│   │       │   ├── documents.py   # 📄 文書管理 + ダウンロード
│   │       │   ├── projects.py    # 📁 プロジェクト管理
│   │       │   ├── workflows.py   # ✅ 承認ワークフロー
│   │       │   ├── audit_logs.py  # 🔍 監査ログ
│   │       │   ├── stats.py       # 📊 統計集計
│   │       │   └── m365.py        # ⚙️ M365 統合設定
│   │       ├── middleware/    # 🔒 Starlette ミドルウェア
│   │       │   └── audit.py       # 全書き込み操作の自動監査ログ
│   │       ├── models/        # SQLAlchemy ORM モデル
│   │       ├── auth/          # JWT 認証・依存性注入
│   │       └── main.py        # FastAPI アプリ本体
│   │
│   └── app/                   # GUIアプリ（計画中）
│
├── tests/
│   └── console/               # pytest + SQLite in-memory (backend 85 / frontend 52 / 計 137 tests)
├── .github/workflows/ci.yml   # CI: lint / test / security scan
└── CLAUDE.md                  # Claude Code プロジェクト設定
```

### API フロー

```
Browser
  │
  ├─ POST /api/v1/auth/token    ─►  JWT Auth (python-jose)
  │                                        │
  ├─ GET  /api/v1/documents/    ─►  AuditMiddleware  ─►  FastAPI Router
  ├─ GET  /api/v1/stats/        ─►       │             │
  ├─ GET  /api/v1/audit-logs/   ─►  (method/path/    SQLAlchemy ORM ──► PostgreSQL
  ├─ GET  /api/v1/workflows/    ─►   status/ip/ms                 │
  ├─ GET  /api/v1/m365/config   ─►   を自動記録)           aiofiles (PDF 保存)
  └─ GET  /api/v1/documents/:id/download ─► FileResponse (PDF ダウンロード)
```

### 主要 API エンドポイント

| エンドポイント | メソッド | 説明 | 権限 |
|---|---|---|---|
| `/api/v1/auth/token` | POST | JWT トークン発行 | 全員 |
| `/api/v1/users/` | GET/POST/PUT/DELETE | ユーザー CRUD | admin |
| `/api/v1/documents/` | GET/POST/DELETE | 文書管理 | 認証済み |
| `/api/v1/documents/{id}/download` | GET | PDF ダウンロード | 認証済み |
| `/api/v1/projects/` | GET/POST/PUT/DELETE | プロジェクト管理 | 認証済み |
| `/api/v1/workflows/` | GET/POST | 承認ワークフロー | 認証済み |
| `/api/v1/audit-logs/` | GET | 監査ログ閲覧 | admin/manager |
| `/api/v1/stats/` | GET | ダッシュボード統計 | 認証済み |
| `/api/v1/m365/config` | GET/PUT | M365 テナント設定 | admin |
| `/api/v1/m365/users/lookup` | GET | AD ユーザー検索 | admin |

---

## 技術スタック

| レイヤー | 技術 | バージョン |
|---|---|---|
| フロントエンド | React + TypeScript + Vite | React 19 / Vite 6 |
| UI スタイル | Tailwind CSS | v4 |
| 状態管理 | zustand | v5 |
| データフェッチ | @tanstack/react-query | v5 |
| HTTP クライアント | axios | v1 |
| ルーティング | react-router-dom | v7 |
| バックエンド | FastAPI (Python) | 0.115+ |
| ORM | SQLAlchemy | 2.0 |
| スキーマ検証 | Pydantic | v2 |
| 認証 | JWT (python-jose + passlib bcrypt) | — |
| データベース | PostgreSQL | 15+ |
| テスト（バックエンド） | pytest + httpx + SQLite（分離） | — |
| Lint / Format | ruff | — |
| CI/CD | GitHub Actions | — |
| コードレビュー | CodeRabbit / Codex Review | — |

---

## セットアップ

### 前提条件

- Node.js >= 20.x
- Python >= 3.11 + pip
- PostgreSQL >= 15

### バックエンド

```bash
cd src/console/backend

# 仮想環境
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 依存インストール
pip install -r requirements.txt

# 環境変数
cp .env.example .env
# .env に DATABASE_URL / SECRET_KEY などを設定

# DB 起動 (PostgreSQL)
# CREATE USER civildx WITH PASSWORD 'password';
# CREATE DATABASE civildx OWNER civildx;

# テーブル作成 (lifespan で自動作成)
uvicorn main:app --reload --port 8000
```

**初回管理者ユーザー作成（bootstrap スクリプト）:**

```python
# scripts/create_admin.py
from models.user import User
from auth.dependencies import get_password_hash
from database import SessionLocal
import uuid

db = SessionLocal()
user = User(
    id=str(uuid.uuid4()),
    email='admin@example.com',
    username='admin',
    full_name='Admin User',
    hashed_password=get_password_hash('AdminPass123!'),
    role='admin',
    status='active',
)
db.add(user)
db.commit()
```

```bash
PYTHONPATH=src/console/backend python scripts/create_admin.py
```

### フォント（PDF処理用）

フォントファイルはリポジトリに含まれていません（容量・ライセンス考慮）。
GitHub push 完了後、以下のスクリプトで16書体を一括ダウンロードできます。

```bash
chmod +x scripts/download-fonts.sh
./scripts/download-fonts.sh
```

| 層 | 内容 | 用途 |
|---|---|---|
| tier1-core | Noto Sans/Serif/Mono JP 計6書体 | 電子納品 PDF/A |
| tier2-compat | IPA + Liberation 計6書体 | 受領 PDF 表示互換 |
| tier3-specialized | BIZ UD + Mono 計4書体 | 安全書類・UD対応 |

保存先: `assets/fonts/`  ←  `.gitignore` でフォントファイル除外済み

### フロントエンド

```bash
cd src/console/frontend

npm install
npm run dev     # http://localhost:5173

# 本番ビルド
npm run build
```

> **注意:** `vite.config.ts` の API プロキシはデフォルトで `http://localhost:8000` を向いています。
> バックエンドが別ポートで動いている場合は変更してください。

### テスト

```bash
# バックエンド（SQLite in-memory で DB 不要）
pytest tests/console/ -v      # 85 tests（カバレッジ 98%）

# フロントエンド
cd src/console/frontend
npm run lint
npm run build
npx vitest run               # 52 tests（Login / ProtectedRoute / authStore / AuditLogs / Dashboard / Documents / Workflows / DocumentPreviewModal）
```

---

## CI ゲート

GitHub Actions (`.github/workflows/ci.yml`) が以下を自動検査します。

| ジョブ | 内容 | 状態 |
|---|---|---|
| `backend-lint` | ruff check + ruff format --check | ✅ |
| `backend-test` | pytest **85 テスト**（SQLite in-memory・カバレッジ 98%） | ✅ |
| `backend-security` | pip-audit による依存脆弱性スキャン | ✅ |
| `frontend-lint-test` | ESLint 0 errors + Vitest **52 テスト** + TypeScript build (Vite) | ✅ |

---

## ロードマップ

| フェーズ | 内容 | 状態 |
|---|---|---|
| Phase 1 — 管理コンソール MVP | JWT 認証・ユーザー・プロジェクト・文書・ワークフロー | ✅ 完成 |
| Phase 2 — Alembic マイグレーション | DB バージョン管理・ゼロダウンタイムスキーマ変更 | ✅ 完成 |
| Phase 3 — 監査ログ・API 拡張 | 監査証跡・統計 API・M365 統合・ダウンロード・テスト 79本 | ✅ 完成 |
| Phase 3.1 — フロントエンドテスト拡充 | Dashboard / Documents / Workflows / AuditLogs 等 52 テスト整備 | ✅ 完成 |
| Phase 3.2 — PDF プレビュー | DocumentPreviewModal による iframe + Blob URL プレビュー（JWT 保護） | ✅ 完成 |
| Phase 4 — API 完全接続 | フロントエンド全画面をリアル API に接続（グレースフルフォールバック） | ✅ 完成 |
| Phase 5 — OCR / AI | 文書要約・自動分類・テキスト抽出 | 📋 未着手 |
| Phase 6 — GUIアプリ | Windows デスクトップ PDF エディタ | 📋 未着手 |
| Phase 7 — 電子納品 | 国交省電子納品要領準拠 PDF/A 変換 | 📋 未着手 |

---

## コントリビューション

Issue 駆動開発を採用しています。変更前に Issue を作成し、ブランチを切ってください。

1. `git checkout -b feat/your-feature`
2. 実装 → テスト追加 → `pytest` / `ruff` クリア
3. PR 作成（CI 成功必須）

## ライセンス

[MIT License](LICENSE)

## 開発体制

このプロジェクトは [Claude Code](https://claude.ai) を主開発ツールとして使用し、
[CodeRabbit](https://coderabbit.ai) および Codex Review によるAIコードレビューを導入しています。
