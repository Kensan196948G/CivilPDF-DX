# API リファレンス

## ベースURL

```
https://<your-domain>/api/v1/
```

## 認証

全エンドポイントは Bearer トークン認証が必要です（Entra ID OIDC）。

## エンドポイント一覧

### PDF文書管理
- `GET /api/v1/documents/` — 文書一覧
- `POST /api/v1/documents/` — 文書アップロード
- `GET /api/v1/documents/{id}` — 文書詳細
- `DELETE /api/v1/documents/{id}` — 文書削除

### ワークフロー
- `POST /api/v1/workflows/` — ワークフロー作成
- `POST /api/v1/workflows/{id}/submit` — 申請
- `POST /api/v1/workflows/{id}/approve` — 承認
- `POST /api/v1/workflows/{id}/reject` — 差戻し

### ユーザー管理
- `GET /api/v1/users/` — ユーザー一覧
- `GET /api/v1/users/me` — 自分の情報

### 監査ログ
- `GET /api/v1/audit-logs/` — ログ一覧（管理者のみ）

詳細仕様は開発進行に合わせて更新します。
