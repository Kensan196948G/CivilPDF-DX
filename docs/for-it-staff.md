# 🖥️ IT 部門向けガイド — CivilPDF-DX

> **対象者**: システム担当者・インフラ担当・IT 部門スタッフ  
> 非エンジニア向け概要は [README.md](../README.md) を参照してください。

---

## 📌 目次

1. [システム全体構成](#-システム全体構成)
2. [前提条件・動作環境](#-前提条件動作環境)
3. [インストール・セットアップ](#-インストールセットアップ)
4. [本番 Docker デプロイ](#-本番-docker-デプロイ推奨)
5. [systemd 常駐設定（LAN サーバー）](#️-systemd-常駐設定lan-サーバー)
6. [セキュリティ設定](#-セキュリティ設定)
7. [ユーザー管理](#-ユーザー管理)
8. [Microsoft 365 / Azure AD 連携](#-microsoft-365--azure-ad-連携)
9. [バックアップ・データ管理](#-バックアップデータ管理)
10. [CI/CD パイプライン](#-cicd-パイプライン)
11. [トラブルシューティング](#-トラブルシューティング)
12. [ディレクトリ構造](#-ディレクトリ構造)

---

## 🏗️ システム全体構成

```mermaid
graph TB
    subgraph LAN["🏢 社内 LAN"]
        CLIENT["💻 クライアント端末\nブラウザ（Chrome / Edge）"]
    end

    subgraph SERVER["🖥️ サーバー（Linux / Windows 11）"]
        subgraph FRONTEND["⚛️ フロントエンド層"]
            VITE["React + Vite\nポート: 5181"]
            NGINX["nginx（本番）\nポート: 8080"]
        end

        subgraph BACKEND["🐍 バックエンド層"]
            FASTAPI["FastAPI（uvicorn）\nポート: 8000"]
            AUTH["JWT 認証\n+ M365 OIDC"]
            AUDIT["監査ミドルウェア\nSHA-256 チェーン"]
        end

        subgraph DATA["🗄️ データ層"]
            SQLITE["SQLite\n（開発・小規模）"]
            POSTGRES["PostgreSQL 16\n（本番推奨）"]
            FILES["PDF ファイル\n./uploads/"]
        end

        subgraph COMPLIANCE["🛡️ コンプライアンス層"]
            TSA["RFC 3161\nタイムスタンプ"]
            PDFA["PDF/A\nバリデーション"]
            GDPR["GDPR 物理削除\nバッチジョブ"]
        end

        subgraph AI["🤖 AI 層"]
            CLAUDE["Claude API\n（Haiku / Sonnet）"]
            FTS["SQLite FTS5\n全文検索"]
        end
    end

    subgraph CLOUD["☁️ 外部サービス（オプション）"]
        M365["Microsoft 365\nAzure AD"]
        TSA_EXT["外部 TSA\n（e-文書法）"]
    end

    CLIENT -->|HTTP| VITE
    CLIENT -->|HTTP| NGINX
    VITE -->|/api/v1/*| FASTAPI
    NGINX -->|プロキシ /api/| FASTAPI
    FASTAPI --> AUTH
    FASTAPI --> AUDIT
    AUTH --> POSTGRES
    AUTH --> SQLITE
    FASTAPI --> FILES
    FASTAPI --> PDFA
    FASTAPI --> TSA
    FASTAPI --> GDPR
    FASTAPI --> CLAUDE
    FASTAPI --> FTS
    AUTH -->|Client Credentials Flow| M365
    TSA -->|RFC 3161| TSA_EXT
```

### 📋 コンポーネント一覧

| コンポーネント           | 役割                                    | ポート                   |
| ------------------------ | --------------------------------------- | ------------------------ |
| 🐍 **FastAPI (uvicorn)** | REST API バックエンド                   | 8000                     |
| ⚛️ **React + Vite**      | SPA フロントエンド（開発・LAN 用）      | 5181                     |
| 🌐 **nginx**             | SPA 配信 + API リバースプロキシ（本番） | 8080                     |
| 🗄️ **PostgreSQL 16**     | 本番データベース                        | 5432（内部）             |
| 📁 **uploads/**          | PDF ファイルストレージ                  | ローカルファイルシステム |

---

## 📋 前提条件・動作環境

### サーバー要件

| 項目                | 最小                          | 推奨                      |
| ------------------- | ----------------------------- | ------------------------- |
| 🖥️ **OS**           | Ubuntu 22.04 LTS / Windows 11 | Ubuntu 22.04 LTS          |
| 💾 **RAM**          | 4 GB                          | 8 GB 以上                 |
| 💿 **ストレージ**   | 50 GB                         | 200 GB 以上（PDF 蓄積分） |
| 🌐 **ネットワーク** | 社内 LAN（100Mbps）           | ギガビット LAN            |

### ソフトウェア要件

| ツール                  | バージョン              | 用途                 |
| ----------------------- | ----------------------- | -------------------- |
| 🐍 **Python**           | 3.12 以上               | バックエンド実行     |
| 📦 **Node.js**          | 20.x 以上（CI は 24.x） | フロントエンドビルド |
| 🐳 **Docker + Compose** | 最新版                  | 本番デプロイ（推奨） |
| 🗄️ **PostgreSQL**       | 15 以上                 | 本番 DB              |

---

## 🛠️ インストール・セットアップ

### 🐍 バックエンド（FastAPI）

```bash
cd src/console/backend

# 1. 仮想環境作成
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 2. 依存インストール
pip install -r requirements.txt
pip install -r requirements-dev.txt   # テスト用（pytest 等）

# 3. 環境変数設定
cp .env.example .env
# .env を編集（下記「必須環境変数」参照）

# 4. 起動（テーブル自動作成込み）
PYTHONPATH=src/console/backend uvicorn main:app --reload --port 8000
```

#### 🔑 必須環境変数（.env）

| 変数                 | 説明                          | 例                                          |
| -------------------- | ----------------------------- | ------------------------------------------- |
| `DATABASE_URL`       | DB 接続 URI                   | `postgresql://user:pass@localhost/civilpdf` |
| `SECRET_KEY`         | JWT 署名キー（32 バイト以上） | `openssl rand -hex 32` で生成               |
| `ANTHROPIC_API_KEY`  | Claude AI API キー            | `sk-ant-...`                                |
| `M365_TENANT_ID`     | Azure AD テナント ID          | UUID                                        |
| `M365_CLIENT_ID`     | Azure アプリ クライアント ID  | UUID                                        |
| `M365_CLIENT_SECRET` | Azure アプリ シークレット     | —                                           |
| `TIMESTAMP_HMAC_KEY` | タイムスタンプ HMAC キー      | `openssl rand -hex 32` で生成               |

#### 👤 初回管理者ユーザー作成

```bash
PYTHONPATH=src/console/backend python scripts/create_admin.py
# 既定: admin@example.com / AdminPass123!
# ⚠️ 初回ログイン後すぐにパスワード変更を実施すること
```

---

### ⚛️ フロントエンド（React + Vite）

```bash
cd src/console/frontend

npm install
npm run dev         # http://localhost:5173（ローカル確認用）
npm run dev:lan     # http://0.0.0.0:5181（LAN 公開）

# 本番ビルド
npm run build
```

#### 🎭 モックモード（バックエンド不要・デモ用）

```bash
npm run dev:mock      # ローカル + モック
npm run dev:lan:mock  # LAN 公開 + モック
```

> ⚠️ **本番環境では絶対に使用しないこと。** モックは認証をバイパスします。  
> `.env` の `VITE_MOCK=1` は dev ビルド限定で、本番ビルド（`vite build`）では自動的に無効化・バンドル除外されます。

---

## 🐳 本番 Docker デプロイ（推奨）

> 📄 完全な手順書: [docs/deployment/docker-production-deployment.md](deployment/docker-production-deployment.md)

```mermaid
graph LR
    subgraph Docker["🐳 Docker Compose (prod)"]
        DB["🗄️ db\nPostgreSQL 16\n内部のみ"]
        BACK["🐍 backend\nFastAPI uvicorn\n内部のみ"]
        FRONT["🌐 frontend\nnginx + SPA\n:8080 公開"]
    end

    CLIENT["💻 クライアント"] -->|":8080"| FRONT
    FRONT -->|"/api/ プロキシ"| BACK
    BACK --> DB
```

```bash
# 1. 環境変数テンプレートをコピー
cp .env.prod.example .env

# 2. 必須シークレット生成
openssl rand -hex 32   # → SECRET_KEY に設定
openssl rand -hex 24   # → POSTGRES_PASSWORD に設定
openssl rand -hex 32   # → TIMESTAMP_HMAC_KEY に設定

# 3. ビルド & 起動
docker compose -f docker-compose.prod.yml up -d --build

# 4. 初回管理者作成
docker compose -f docker-compose.prod.yml exec backend python create_admin.py

# 5. 動作確認
curl http://localhost:8080/health
```

---

## 🖥️ systemd 常駐設定（LAN サーバー）

Docker を使わない場合（開発環境・LAN 公開用）:

```bash
# インストール
bash deploy/install-systemd.sh

# 状態確認
systemctl --user status civilpdf-frontend.service
systemctl --user status civilpdf-backend.service

# ログアウト後も常駐
loginctl enable-linger $USER
```

| サービス                    | ポート | 説明                     |
| --------------------------- | ------ | ------------------------ |
| `civilpdf-backend.service`  | 8000   | FastAPI（uvicorn）       |
| `civilpdf-frontend.service` | 5181   | Vite dev:lan（LAN 公開） |

---

## 🔐 セキュリティ設定

### 認証・認可フロー

```mermaid
sequenceDiagram
    participant C as 💻 クライアント
    participant F as ⚛️ Frontend
    participant B as 🐍 Backend
    participant DB as 🗄️ DB
    participant M365 as ☁️ Azure AD

    C->>F: ログイン（email / password）
    F->>B: POST /api/v1/auth/token
    B->>DB: パスワード検証（bcrypt）
    B->>B: JWT 生成（HS256）
    B-->>F: access_token + refresh_token
    F-->>C: Cookie / LocalStorage 保存

    C->>F: API リクエスト
    F->>B: Bearer token 付与
    B->>B: JWT 署名検証
    B->>M365: M365 非対話式認証（オプション）
    B-->>C: レスポンス + 監査ログ自動記録
```

### セキュリティ機構一覧

| 機能                      | 実装                                   | 備考                         |
| ------------------------- | -------------------------------------- | ---------------------------- |
| 🔑 **パスワードハッシュ** | bcrypt（passlib）                      | ソルト自動付与               |
| 🎟️ **JWT 署名**           | HS256（python-jose）                   | access 30分 / refresh 7日    |
| 🔒 **M365 資格情報**      | Fernet 対称暗号化（cryptography 46.x） | DB 保存前に暗号化            |
| 🔗 **監査チェーン**       | SHA-256 hash chain                     | 改ざん検知エンドポイント付き |
| 🛡️ **依存脆弱性スキャン** | pip-audit                              | CI で毎回実行                |
| 🌐 **CORS**               | FastAPI CORSMiddleware                 | オリジン制限設定可           |

### RBAC 権限テーブル

| 操作                    | 👤 admin | 👔 manager | 🔧 engineer | 👁️ viewer |
| ----------------------- | :------: | :--------: | :---------: | :-------: |
| ユーザー管理（CRUD）    |    ✅    |     ❌     |     ❌      |    ❌     |
| M365 テナント設定       |    ✅    |     ❌     |     ❌      |    ❌     |
| GDPR 削除リクエスト実行 |    ✅    |     ❌     |     ❌      |    ❌     |
| 監査ログ閲覧            |    ✅    |     ✅     |     ❌      |    ❌     |
| 電子納品 ZIP 生成       |    ✅    |     ✅     |     ❌      |    ❌     |
| 文書アップロード・削除  |    ✅    |     ✅     |     ✅      |    ❌     |
| 承認ワークフロー操作    |    ✅    |     ✅     |     ✅      |    ❌     |
| 文書・プロジェクト閲覧  |    ✅    |     ✅     |     ✅      |    ✅     |
| ダッシュボード閲覧      |    ✅    |     ✅     |     ✅      |    ✅     |

---

## 👥 ユーザー管理

### ユーザー作成・管理

- 管理者ユーザーはシステムの「ユーザー管理」画面から GUI で追加
- M365（Azure AD）連携時は AD ユーザー検索・同期が可能
- ロール変更も管理画面から即時反映

### 初期パスワードポリシー

```
初期: AdminPass123!（管理者スクリプト作成時）
要件: 英大文字・英小文字・数字・記号を含む 8 文字以上
初回ログイン後: 必ず変更すること
```

---

## 🏢 Microsoft 365 / Azure AD 連携

### 必要な Azure 設定

```mermaid
graph TD
    A["Azure Portal"] --> B["アプリの登録"]
    B --> C["クライアントシークレット生成"]
    B --> D["API アクセス許可\nUser.Read.All（管理者同意）"]
    B --> E["テナント ID・クライアント ID 取得"]
    E --> F["CivilPDF-DX の .env に設定"]
    C --> F
```

| 設定項目        | Azure Portal での場所                                                |
| --------------- | -------------------------------------------------------------------- |
| `TENANT_ID`     | Azure Active Directory → プロパティ → テナント ID                    |
| `CLIENT_ID`     | アプリの登録 → 概要 → アプリケーション（クライアント）ID             |
| `CLIENT_SECRET` | アプリの登録 → 証明書とシークレット → 新しいクライアントシークレット |

> ℹ️ Client Credentials Flow（非対話式）を使用。ユーザーへの同意ダイアログは不要。

---

## 💾 バックアップ・データ管理

### バックアップ対象

| 対象                | 場所                    | 推奨頻度                             |
| ------------------- | ----------------------- | ------------------------------------ |
| 📊 **データベース** | PostgreSQL              | 毎日（pg_dump）                      |
| 📁 **PDF ファイル** | `uploads/` ディレクトリ | 毎日（rsync / バックアップサーバー） |
| ⚙️ **設定ファイル** | `.env`                  | 変更時（シークレット管理に注意）     |

### バックアップコマンド例（PostgreSQL）

```bash
# バックアップ
pg_dump -U civilpdf civilpdf_db > backup_$(date +%Y%m%d).sql

# リストア
psql -U civilpdf civilpdf_db < backup_20260614.sql
```

### データ保持ポリシー（電子帳簿保存法対応）

システムが自動的に以下の保持ポリシーを適用します。

| 書類種別     | 保持期間 |
| ------------ | -------- |
| 税務関連書類 | 7 年     |
| 建設工事書類 | 10 年    |
| 公共工事書類 | 15 年    |
| 電子納品書類 | 永続     |

---

## ⚙️ CI/CD パイプライン

```mermaid
graph LR
    subgraph CI["🔄 GitHub Actions CI"]
        L1["🔍 backend-lint\nruff check + format"]
        T1["🧪 backend-test\npytest 234件 カバレッジ98%"]
        S1["🛡️ backend-security\npip-audit"]
        L2["🔍 frontend-lint-test\nESLint + Vitest 132件"]
        E2E["🎭 frontend-e2e\nPlaywright 3件"]
        IT["🔗 integration-test\nE2E 20件"]
    end

    subgraph GATE["✅ マージゲート"]
        PR["Pull Request"]
        ALL["全ジョブ成功"]
        MERGE["main へ merge"]
    end

    PR --> L1
    PR --> T1
    PR --> S1
    PR --> L2
    PR --> E2E
    PR --> IT
    L1 --> ALL
    T1 --> ALL
    S1 --> ALL
    L2 --> ALL
    E2E --> ALL
    IT --> ALL
    ALL --> MERGE
```

| ジョブ               | 内容                                                 | 所要時間目安 |
| -------------------- | ---------------------------------------------------- | ------------ |
| `backend-lint`       | ruff check + ruff format --check                     | ~30秒        |
| `backend-test`       | pytest 234 件（SQLite in-memory）カバレッジ 98%      | ~2分         |
| `backend-security`   | pip-audit 依存脆弱性スキャン                         | ~1分         |
| `frontend-lint-test` | ESLint 0 errors + Vitest 132 件 + TypeScript build   | ~3分         |
| `frontend-e2e`       | Playwright E2E 3 件（chromium 実ブラウザ）           | ~2分         |
| `integration-test`   | E2E テスト 20 件（認証 / 文書 / 承認 / GDPR / RBAC） | ~3分         |

---

## 🚨 トラブルシューティング

### よくある問題と対処

| 症状                        | 原因                             | 対処                                 |
| --------------------------- | -------------------------------- | ------------------------------------ |
| ❌ ログインできない         | JWT シークレット不一致           | `.env` の `SECRET_KEY` を確認        |
| ❌ PDF アップロード失敗     | `uploads/` ディレクトリ権限      | `chmod 755 uploads/` を実行          |
| ❌ AI 機能が動作しない      | Anthropic API キー未設定         | `.env` の `ANTHROPIC_API_KEY` を設定 |
| ❌ M365 連携エラー          | クライアントシークレット期限切れ | Azure Portal でシークレットを再生成  |
| ⚠️ DB 接続エラー            | PostgreSQL 未起動                | `systemctl start postgresql`         |
| ⚠️ フロントエンド起動しない | Node.js バージョン不一致         | Node.js 20.x 以上にアップデート      |

### ログ確認コマンド

```bash
# バックエンドログ（systemd）
journalctl --user -u civilpdf-backend.service -f

# フロントエンドログ
journalctl --user -u civilpdf-frontend.service -f

# Docker ログ
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml logs -f frontend

# 監査ログ確認（API）
curl -H "Authorization: Bearer <admin_token>" \
  http://localhost:8000/api/v1/audit-logs/?limit=50
```

### ヘルスチェック

```bash
# バックエンド
curl http://localhost:8000/health

# フロントエンド（本番）
curl http://localhost:8080/health

# DB 接続確認（Docker）
docker compose -f docker-compose.prod.yml exec db pg_isready
```

---

## 📁 ディレクトリ構造

```
CivilPDF-DX/
├── 📁 src/
│   └── console/
│       ├── 🐍 backend/                  # FastAPI バックエンド
│       │   ├── api/                     # REST エンドポイント（14 モジュール）
│       │   ├── models/                  # SQLAlchemy ORM モデル
│       │   ├── services/                # ドメインサービス（TSA・GDPR・PDFA 等）
│       │   ├── middleware/              # 監査ミドルウェア（SHA-256 チェーン）
│       │   ├── auth/                   # JWT 認証・依存性注入
│       │   └── main.py                 # FastAPI アプリ本体
│       └── ⚛️ frontend/                # React フロントエンド
│           └── src/
│               ├── api/                # Axios API クライアント
│               ├── components/enterprise/views/  # 12 画面コンポーネント
│               ├── mock/               # モックアダプター（dev 専用）
│               └── store/             # Zustand 認証ストア
├── 🧪 tests/
│   ├── console/                        # pytest ユニットテスト（234 件）
│   └── integration/                    # E2E 統合テスト（20 件）
├── 🚀 deploy/
│   ├── civilpdf-backend.service        # systemd ユニット
│   ├── civilpdf-frontend.service
│   └── install-systemd.sh
├── 📄 docs/                            # 各種設計ドキュメント
├── ⚙️ .github/workflows/ci.yml         # GitHub Actions CI
├── 🐳 docker-compose.yml               # 開発用
└── 🐳 docker-compose.prod.yml          # 本番用
```

---

## 📚 関連ドキュメント

| 文書                | リンク                                                                                        |
| ------------------- | --------------------------------------------------------------------------------------------- |
| 📊 技術スタック詳細 | [docs/tech-stack.md](tech-stack.md)                                                           |
| 🏗️ システム構成図   | [docs/architecture/system-architecture.md](architecture/system-architecture.md)               |
| 🚀 本番デプロイ手順 | [docs/deployment/docker-production-deployment.md](deployment/docker-production-deployment.md) |
| 🌐 API リファレンス | [docs/api/README.md](api/README.md)                                                           |
| 🗄️ DB 設計書        | [docs/database-design.md](database-design.md)                                                 |
| 🪟 Windows 11 展開  | [docs/windows-deployment.md](windows-deployment.md)                                           |

---

_最終更新: 2026-06-14 | CivilPDF-DX Phase 9 / Release Ready_
