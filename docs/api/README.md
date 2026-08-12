# CivilPDF-DX API リファレンス

> 実装された FastAPI ルーターから 2026-08-12 時点で生成した一覧です。
> OpenAPI の正本はアプリの `/openapi.json`（Swagger UI: `/docs`）です。

## ベース URL

```
https://<your-domain>/api/v1/
```

## 認証

- API は原則 `Authorization: Bearer <access_token>` が必要です。
- トークン取得: `POST /api/v1/auth/token`（フォーム認証）
- トークン更新: `POST /api/v1/auth/refresh`（`refresh_token` のみこのエンドポイントで利用）
- Microsoft 365 は**非対話ブリッジ**（`POST /api/v1/auth/m365/login`）であり、Entra ID OIDC の必須化は未実装です（要件上は将来課題）。
- 認証不要: `GET /health`、`GET /`

## エンドポイント一覧

### 認証

| メソッド | パス | 説明 |
|---|---|---|
| POST | `/api/v1/auth/token` | メール/パスワードでトークン発行 |
| POST | `/api/v1/auth/refresh` | refresh token でトークン更新 |
| GET | `/api/v1/auth/me` | ログインユーザー情報 |
| PATCH | `/api/v1/auth/me` | 自分自身のプロフィール更新 |
| POST | `/api/v1/auth/me/password` | パスワード変更 |
| POST | `/api/v1/auth/m365/login` | M365 非対話ログインブリッジ |

### ユーザー管理

| メソッド | パス | 説明 |
|---|---|---|
| GET | `/api/v1/users/` | ユーザー一覧 |
| POST | `/api/v1/users/` | ユーザー作成 |
| GET | `/api/v1/users/{user_id}` | ユーザー詳細 |
| PATCH | `/api/v1/users/{user_id}` | ユーザー更新 |
| DELETE | `/api/v1/users/{user_id}` | ユーザー削除 |

### PDF 文書管理

| メソッド | パス | 説明 |
|---|---|---|
| GET | `/api/v1/documents/` | 文書一覧 |
| POST | `/api/v1/documents/` | PDF アップロード |
| GET | `/api/v1/documents/{doc_id}` | 文書詳細 |
| PATCH | `/api/v1/documents/{doc_id}` | 文書メタデータ更新 |
| GET | `/api/v1/documents/{doc_id}/download` | PDF ダウンロード |
| POST | `/api/v1/documents/{doc_id}/timestamp` | タイムスタンプ付与 |
| GET | `/api/v1/documents/{doc_id}/timestamp/verify` | タイムスタンプ検証 |
| DELETE | `/api/v1/documents/{doc_id}` | 文書削除 |

### ワークフロー

| メソッド | パス | 説明 |
|---|---|---|
| GET | `/api/v1/workflows/` | ワークフロー一覧 |
| POST | `/api/v1/workflows/` | ワークフロー作成 |
| GET | `/api/v1/workflows/{workflow_id}` | ワークフロー詳細 |
| POST | `/api/v1/workflows/{workflow_id}/steps/{step_id}/decide` | 承認/却下決定 |

### プロジェクト / 電子納品

| メソッド | パス | 説明 |
|---|---|---|
| GET | `/api/v1/projects/` | プロジェクト一覧 |
| POST | `/api/v1/projects/` | プロジェクト作成 |
| GET | `/api/v1/projects/{project_id}` | プロジェクト詳細 |
| POST | `/api/v1/projects/{project_id}/members/{user_id}` | メンバー追加 |
| DELETE | `/api/v1/projects/{project_id}/members/{user_id}` | メンバー削除 |
| GET | `/api/v1/projects/{project_id}/electronic-delivery/check` | 電子納品チェック |
| POST | `/api/v1/projects/{project_id}/electronic-delivery` | 電子納品 ZIP 生成 |

### 監査ログ / 統計

| メソッド | パス | 説明 |
|---|---|---|
| GET | `/api/v1/audit-logs/` | 監査ログ一覧（管理者） |
| GET | `/api/v1/audit-logs/verify` | 監査チェーン検証（管理者） |
| GET | `/api/v1/stats/` | 全体統計 |
| GET | `/api/v1/stats/security` | セキュリティイベント統計（管理者） |
| GET | `/api/v1/stats/security-config` | セキュリティ設定統計 |
| GET | `/api/v1/stats/projects` | プロジェクト統計 |
| GET | `/api/v1/stats/daily` | 日次統計 |

### 組織 / M365 / OCR / AI

| メソッド | パス | 説明 |
|---|---|---|
| GET/POST | `/api/v1/organizations/` | 組織一覧/作成 |
| GET | `/api/v1/organizations/tree` | 組織ツリー |
| GET/PATCH/DELETE | `/api/v1/organizations/{org_id}` | 組織詳細/更新/削除 |
| GET | `/api/v1/organizations/{org_id}/members` | 組織メンバー一覧 |
| GET/PUT | `/api/v1/m365/config` | M365 設定取得/更新（管理者） |
| POST | `/api/v1/m365/test-connection` | M365 接続テスト（管理者） |
| GET | `/api/v1/m365/users/lookup` | M365 ユーザー検索 |
| POST | `/api/v1/ocr/process` | OCR 開始 |
| GET | `/api/v1/ocr/jobs/{job_id}` | OCR 状態 |
| GET | `/api/v1/ocr/jobs/{job_id}/result` | OCR 結果 |
| POST | `/api/v1/ai/documents/{document_id}/classify` | AI 分類 |
| POST | `/api/v1/ai/documents/{document_id}/extract` | 構造化抽出 |
| GET | `/api/v1/ai/documents/{document_id}/summary` | AI 要約 |
| GET/PUT | `/api/v1/ai-config` | AI 設定取得/更新（管理者） |
| POST | `/api/v1/ai-config/test` | AI 接続テスト（管理者） |

### 検索 / Editor 連携 / リビジョン / プライバシー / アプリ配布

| メソッド | パス | 説明 |
|---|---|---|
| GET | `/api/v1/search/documents` | 全文検索 |
| POST | `/api/v1/search/documents/reindex` | 再インデックス |
| GET | `/api/v1/search/documents/suggest` | サジェスト |
| POST | `/api/v1/documents/{doc_id}/review-sidecar` | Editor レビュー情報取込 |
| GET | `/api/v1/documents/{doc_id}/review-sidecar` | Editor レビュー情報取得 |
| POST | `/api/v1/documents/{doc_id}/flatten-check` | 平坦化チェック |
| POST | `/api/v1/documents/{doc_id}/editor-events` | Editor イベント記録 |
| GET | `/api/v1/documents/{doc_id}/workflow-status` | Editor 向けワークフロー状態 |
| POST | `/api/v1/documents/{doc_id}/revisions` | リビジョン登録 |
| GET | `/api/v1/documents/{doc_id}/revisions` | リビジョン一覧 |
| DELETE | `/api/v1/privacy/users/{user_id}/data` | GDPR 削除要求 |
| GET | `/api/v1/privacy/users/{user_id}/export` | データエクスポート |
| POST | `/api/v1/privacy/consent` | 同意記録 |
| GET | `/api/v1/privacy/consent/{user_id}` | 同意状況 |
| POST | `/api/v1/privacy/admin/run-deletion-job` | 物理削除ジョブ実行 |
| GET | `/api/v1/apps/releases` | アプリ配布リリース一覧 |
| GET | `/api/v1/apps/release-notes` | リリースノート |
| GET | `/api/v1/apps/build-info` | ビルド情報 |
| GET | `/api/v1/apps/download/{package_id}` | ダウンロード URL |

## 補足

- 各エンドポイントの詳細スキーマ・アクセス権限は `/openapi.json` を参照してください。
- 存在しない旧エンドポイント（`/workflows/{id}/submit`・`/approve`・`/reject`・`/users/me` 等）は本リポジトリには未実装です。
