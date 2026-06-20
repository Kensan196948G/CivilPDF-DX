# Changelog

すべての注目すべき変更点はこのファイルに記録されます。

[Semantic Versioning](https://semver.org/) に従います。

---

## [Unreleased]

### 追加 (アプリ配信ページ本番化 — PDF Editor Client 配布窓口)

- **リリースノート API** `GET /api/v1/apps/release-notes`（`?channel=stable|beta|insider`）
  - 配信ページのリリースノートをフロント直書きから backend の単一の真実へ移管
- **ビルド情報 API** `GET /api/v1/apps/build-info`
  - 製品/安定版/ビルド番号/コミット/ビルド日/対応OS/最低サポート版を返却
  - `APPS_BUILD_*` 環境変数をリクエスト時読み取り（秘密情報は非掲載）
- **配布物チェックサム**: `APPS_SHA256_<PKG_ID>` から SHA-256 を解決し `releases`/`download` に反映
- **macOS `.pkg` パッケージ**を追加（`.dmg` 維持・MDM/Jamf 一括展開向け）
- **Windows `.msi` インストーラー**を追加（`.exe` と選択式・GPO/SCCM サイレント展開向け）
- 配信ページ UI: リリースノート/ビルド情報ボタンを実 API 化、`dev:mock` で配信ページが動作、展開対象/KPI は「デモ」明示
- 運用手順: `docs/deployment/app-distribution.md` を追加

### 計画中

- アプリ配信: 展開対象/KPI の実 MDM（Intune / Jamf）連携
- PDF Editor デスクトップ本体 + ビルドパイプライン新規構築（Issue #62 / Scope B）

---

## [0.7.0] — 2026-06-01

### 追加 (Phase 7: AI/OCR 統合)

- **AI 文書分類** `POST /api/v1/ai/documents/{id}/classify`
  - Claude Haiku による建設業図面自動分類（平面図/立面図/断面図/構造図/設備図）
  - プロジェクト種別自動タグ付け（土木/建築/設備/道路/橋梁）
  - 分類結果を `Document.tags` + `extra_data["ai_classification"]` に保存
- **AI 構造データ抽出** `POST /api/v1/ai/documents/{id}/extract`
  - 工事名・施工会社・現場住所・金額・工期・担当者・チェックリストを JSON 抽出
- **AI 要約** `GET /api/v1/ai/documents/{id}/summary`
  - 承認者向け 3〜5 行自動サマリー生成
- **セマンティック検索** `GET /api/v1/search/documents`
  - SQLite FTS5 全文検索（unicode61 トークナイザー、プレフィックス検索対応）
  - `mode=semantic` で Claude AI がクエリを建設業専門語に展開（「橋梁」→「bridge, RC構造, 補修…」）
  - `POST /search/documents/reindex` — 管理者向け FTS5 インデックス再構築
  - `GET /search/documents/suggest` — AI クエリ拡張候補
- フロントエンド: Documents ページに AI 分類ボタン・AI タグ列・分類結果モーダル追加
- フロントエンド: AI 検索バー UI（keyword/semantic モード切替・スニペット強調表示）
- `anthropic>=0.40.0` を requirements.txt に追加

### 修正

- **IDOR 脆弱性 [HIGH]** — AI API 全エンドポイントに `_check_document_access()` 追加
  - 非所有者・非管理者への 404 隠蔽（403 ではなく 404 で文書存在を秘匿）
- **XSS 修正** — 検索スニペット表示で `dangerouslySetInnerHTML` → React `split+map` 安全描画
- **SQLite JSON カラム変換** — FTS JOIN 時の tags フィールドを `json.loads()` で安全変換

### テスト追加

- `tests/console/test_ai.py`: AI API 13 件（IDOR 防御テスト含む）
- `tests/console/test_search.py`: Search API 13 件（keyword/semantic/reindex/RBAC）

---

## [0.6.1] — 2026-05-26

### 追加 (Phase 6.1: プロフィール管理 API)

- `PATCH /api/v1/auth/me` — 認証済みユーザーのフルネーム更新
- `POST /api/v1/auth/me/password` — パスワード変更（現在パスワード確認付き）
- Settings ページ: プロフィール編集フォーム・パスワード変更フォーム
- auth テスト 7 件追加（合計 164 件）
- フロントエンドテスト 103 件通過

### 修正

- FastAPI 0.136.3 + starlette 1.1.0 アップグレード（**PYSEC-2026-161** セキュリティ修正）
- `HTTP_422_UNPROCESSABLE_CONTENT` / `HTTP_413_CONTENT_TOO_LARGE` 定数名修正
- conftest DB override を `scope=package` fixture に移動（pytest 干渉解消）
- OCR API: pypdf 実装（stub 削除）

---

## [0.5.1] — 2026-05-19

### 追加 (Phase 5.1: コンプライアンス基盤)

- PDF/A バリデーター（ISO 14289 準拠、pypdf + veraPDF フォールバック）
- GDPR Art.17 削除権（論理削除マーク → 物理削除バッチジョブ）
- ISO 19650 メタデータ UI（文書種別・プロジェクト情報・改訂番号）
- プライバシー管理（同意記録 ConsentRecord、CCPA 対応）
- 保持ポリシー管理（電子帳簿保存法 7 年、書類種別別期間）
- 監査チェーン（SHA-256 ハッシュチェーン、改ざん検知エンドポイント）
- M365 非対話式認証統合（Fernet 暗号化、Client Credentials Flow）
- ワークフロー詳細 UI（承認ステップ操作モーダル、RBAC 承認/却下）
- PDF プレビュー機能（Blob URL + iframe、JWT 保護、Escape/× クローズ）
- E2E 統合テスト 20 件（認証/文書/承認/GDPR/RBAC 5 シナリオ）

---

## [0.4.0] — 2026-05-15

### 追加 (Phase 4: フロントエンド API 接続)

- フロントエンド全画面リアル API 接続（グレースフルフォールバック）
- Dashboard KPI stats API 統合（getStats エンドポイント）
- Projects ページ RBAC + 検索 + 削除テスト（13 件）
- vitest `.claude/` 除外設定（ClaudeOS 内部テスト混入防止）
- Settings ページ実装（プロフィール/システム情報/セキュリティポリシー）

---

## [0.3.0] — 2026-05-12

### 追加 (Phase 3: 監査・M365・PDF)

- 監査ログ機能（AuditLog モデル + API + UI）
- 統計 API（ダッシュボード KPI 集計）
- frontend LAN systemd 公開（dev:lan @ port 5181）
- フロントエンドテスト拡充（Dashboard/Documents/Workflows 等）

---

## [0.2.0] — 2026-05-11

### 追加 (Phase 1–2: 基盤整備)

- FastAPI バックエンド基盤（JWT 認証・RBAC・PDF 管理 API・承認ワークフロー API）
- SQLAlchemy モデル設計（User/Document/Project/Workflow）
- React フロントエンド基盤（Vite + TanStack Query + Zustand）
- Alembic マイグレーション
- Docker Compose
- GitHub Actions CI/CD（lint / test / security scan）
- ユニットテスト 157 件（backend 98% カバレッジ）

---

[Unreleased]: https://github.com/Kensan196948G/CivilPDF-DX/compare/v0.7.0...HEAD
[0.7.0]: https://github.com/Kensan196948G/CivilPDF-DX/compare/v0.6.1...v0.7.0
[0.6.1]: https://github.com/Kensan196948G/CivilPDF-DX/compare/v0.5.1...v0.6.1
[0.5.1]: https://github.com/Kensan196948G/CivilPDF-DX/compare/v0.4.0...v0.5.1
[0.4.0]: https://github.com/Kensan196948G/CivilPDF-DX/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/Kensan196948G/CivilPDF-DX/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/Kensan196948G/CivilPDF-DX/compare/v0.1.0...v0.2.0
