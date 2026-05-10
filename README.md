# CivilPDF-DX

**現場が止まらないPDF管理を。**
図面の赤入れ、承認フロー、電子納品チェックまでを一気通貫でカバーする、建設業特化のオープンソースPDFプラットフォームです。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/kensan1969/CivilPDF-DX/actions/workflows/ci.yml/badge.svg)](https://github.com/kensan1969/CivilPDF-DX/actions/workflows/ci.yml)
[![Built with Claude Code](https://img.shields.io/badge/Built%20with-Claude%20Code-blueviolet)](https://claude.ai)

---

## 概要

CivilPDF-DX は、建設・土木業における PDF 業務を統合管理するプラットフォームです。

| モジュール | 説明 | 状態 |
|---|---|---|
| 管理コンソール（WebUI） | ユーザー管理・文書管理・プロジェクト管理・承認ワークフロー | ✅ MVP 完成 |
| GUIアプリ（Windows exe） | PDF閲覧・編集・注釈・OCR・電子印鑑・図面赤入れ | 📋 計画中 |

---

## 管理コンソール MVP 機能

| 機能 | 詳細 |
|---|---|
| 🔐 JWT 認証 | ログイン / ログアウト / トークン自動更新 |
| 👥 ユーザー管理 | CRUD・ロールベースアクセス（admin / manager / engineer / viewer） |
| 📁 プロジェクト管理 | 作成・一覧・削除・ステータス管理 |
| 📄 文書管理 | PDF アップロード（最大 50MB）・一覧・削除・種別分類 |
| ✅ 承認ワークフロー | 多段階承認（ステップ単位の承認 / 却下 / コメント） |

---

## アーキテクチャ

```
CivilPDF-DX/
├── src/
│   ├── console/               # 管理コンソール（MVP）
│   │   ├── frontend/          # React 19 + TypeScript + Tailwind CSS v4
│   │   │   └── src/
│   │   │       ├── api/       # axios クライアント + 各ドメイン API
│   │   │       ├── components/ # Layout / ProtectedRoute
│   │   │       ├── pages/     # Dashboard / Documents / Projects / Workflows / Users / Login
│   │   │       └── store/     # zustand auth store
│   │   └── backend/           # FastAPI + SQLAlchemy 2.0 + PostgreSQL
│   │       ├── api/           # REST エンドポイント (auth / users / documents / projects / workflows)
│   │       ├── models/        # SQLAlchemy ORM モデル
│   │       ├── auth/          # JWT 認証・依存性注入
│   │       └── main.py        # FastAPI アプリ本体
│   │
│   └── app/                   # GUIアプリ（計画中）
│
├── tests/
│   └── console/               # pytest + SQLite in-memory (35 tests)
├── .github/workflows/ci.yml   # CI: lint / test / security scan
└── CLAUDE.md                  # Claude Code プロジェクト設定
```

### API フロー

```
Browser
  │
  ├─ GET /api/v1/documents/    ─► FastAPI Router
  │                                  │
  ├─ POST /api/v1/auth/token   ─►  JWT Auth (python-jose)
  │                                  │
  └─ POST /api/v1/documents/   ─►  SQLAlchemy ORM ──► PostgreSQL
                                     │
                               aiofiles (PDF 保存)
```

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
pytest tests/console/ -v      # 35 tests

# フロントエンド
cd src/console/frontend
npm run lint
npm run build
```

---

## CI ゲート

GitHub Actions (`.github/workflows/ci.yml`) が以下を自動検査します。

| ジョブ | 内容 |
|---|---|
| `backend-lint` | ruff check + ruff format --check |
| `backend-test` | pytest 35 テスト（SQLite） |
| `backend-security` | pip-audit による依存脆弱性スキャン |
| `frontend-lint-test` | ESLint + TypeScript build |

---

## ロードマップ

| フェーズ | 内容 | 状態 |
|---|---|---|
| Phase 1 — 管理コンソール MVP | JWT 認証・ユーザー・プロジェクト・文書・ワークフロー | ✅ 完成 |
| Phase 2 — Alembic マイグレーション | DB バージョン管理・ゼロダウンタイムスキーマ変更 | 📋 未着手 |
| Phase 3 — 監査ログ | 全操作の監査証跡・閲覧 UI | 📋 未着手 |
| Phase 4 — OCR / AI | 文書要約・自動分類・テキスト抽出 | 📋 未着手 |
| Phase 5 — GUIアプリ | Windows デスクトップ PDF エディタ | 📋 未着手 |
| Phase 6 — 電子納品 | 国交省電子納品要領準拠 PDF/A 変換 | 📋 未着手 |

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
