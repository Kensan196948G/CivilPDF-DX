# Changelog

すべての注目すべき変更点はこのファイルに記録されます。

[Semantic Versioning](https://semver.org/) に従います。

---

## [Unreleased]

### 2026-08-13 — MVP / Prototype 公開（v0.9.0）

- **P0 修正**: `LICENSE` に残っていた未解決の Git 競合マーカーを除去（Copyright を Kensan196948G に一本化。GitHub のライセンス検出が復帰）
- **セキュリティ**: `python-jose`（ecdsa PYSEC-2026-1325 の影響）→ `PyJWT 2.13` へ移行し、pip-audit の ignore を撤廃（Issue #106 解消）
- **レート制限**: 認証エンドポイント（`/auth/token`・`/auth/m365/login` 10回/60秒/IP、`/auth/refresh` 30回、パスワード再設定 5回）にスライディングウィンドウ制限を追加（429 + `Retry-After`）
- **CSV エクスポート**: `GET /documents/export.csv`（RBAC 準拠）と `GET /audit-logs/export.csv`（管理者限定・出力自体を監査）。UTF-8 BOM・数式インジェクション対策済み。WebUI に出力ボタンを追加
- **MVP ダミーデータ**: `scripts/seed_demo_data.py`（冪等・`--reset` 対応）— 組織6/ユーザー10/プロジェクト5/文書21（PDF実ファイル）/ワークフロー5/通知/監査チェーン/DX同期/同意記録を架空値で投入
- **MVP 環境**: `docker-compose.mvp.yml`（SQLite + seed 自動投入）、`scripts/mvp-smoke.py`（実 HTTP 15 項目検証）、Cloudflare Tunnel `civilpdf-mvp` を新設
- **公開 URL**: 本番 https://civilpdf.mirai-dx-platform.com/ / MVP https://civilpdf-mvp.mirai-dx-platform.com/
- **文書整合**: README・API リファレンス・要件定義書の実装状態・WebUI 画面一覧・Runbook のバージョン表記を実装と同期。`VERSION` 0.9.0
- **テスト**: 新規 11 件（レート制限 6 + CSV エクスポート 3 + フロント CSV ヘルパー 2）。conftest のテスト鍵を 32 バイト以上へ。CI 実測 691 件（backend 394 + integration 20 + frontend vitest 271 + Playwright 6）・12/12 success

### 2026-08-12 — 本番適用（systemd / SQLite）

- `alembic upgrade head` を本番DBへ適用（h4x5y6z7a8b9 → **k1l2m3n4o5p6**）:
  login lockout・password reset・notifications・**dx_sync_metrics**
- 本番env に `TIMESTAMP_HMAC_KEY` を追加（production fail-fast 対応）
- backend / frontend を再起動し、`GET /api/v1/stats/dx-sync`（401）・
  frontend（HTTP 200）・`dx_sync_metrics` テーブル作成を確認
- バックアップ: `~/civildx-backups/pre-dx-metrics-20260812/`

### 2026-08-12 — 本番DBを Neon PostgreSQL へ移行

- Neon プロジェクト `civilpdf-dx-production`（PG 18.4・aws-ap-southeast-1）を作成し、
  `alembic upgrade head`（k1l2m3n4o5p6）を適用
- `scripts/migrate-sqlite-to-neon.py` を新設し、SQLite → PostgreSQL のデータ移行を実行
  （日時/Boolean/JSON 変換・整数PKシーケンス同期・行数検証を内包）
- `~/.config/civilpdf/civilpdf.env` の `DATABASE_URL` を Neon へ切替・backend 再起動
  （alembic `PostgresqlImpl`・/health 200・/stats/dx-sync 401 を確認）
- `scripts/backup-production.sh` / `deploy/civilpdf-backup.service` を PostgreSQL 対応へ更新
  （pg_dump 18 自動選択・custom format・pg_restore 検証）
- ロールバック手順を docs/deployment/neon-postgresql-migration.md に更新

### 2026-08-12 — 復元訓練の PostgreSQL 対応（Issue #130）

- `scripts/restore-drill.sh` が PostgreSQL バックアップ（`civilpdf.dump`）を検出すると、
  `pg_restore --clean --if-exists --no-owner --no-acl` で復元し、alembic head・uploads 件数・
  /health・認証フローまで検証（`--database-url` / `DRILL_DATABASE_URL` 対応）
- Neon 一時ブランチで実ドリルを実施し **DRILL PASS**（2026-08-12T23:47 JST・訓練後ブランチ削除）
- 全文検索（tsvector + GIN）は実装済みであることを本番 Neon で確認（search_vector 列・GIN インデックス）

### 2026-08-12 — DX 同期監視基盤と sidecar 上限拡大（Editor v1.12.3 連携）

- **`dx_sync_metrics` テーブル新設**（migration `k1l2m3n4o5p6`）— review-sidecar 送信の
  成功/失敗をサーバー側で 1 リクエスト 1 行記録（ミドルウェア `middleware/dx_metrics.py`）。
  監査ログとは独立した SLI 集計用の正本
- **`GET /api/v1/stats/dx-sync` 追加**（Admin 限定）— 総数/成功/失敗/成功率（全体・30日）、
  エラー種別（auth/rbac/not_found/too_large/invalid/server）、直近 6 か月の月次系列
- **sidecar 上限を 2 MiB → 8 MiB に拡大**（`api/editor.py`）— Editor v1.12.3 と整合。
  写真級の印鑑画像が増える場合はクライアント圧縮へ移行（Editor Issue #92）
- テスト: `test_editor_integration.py`（413・metrics 記録 3 件）、`test_stats.py`
  （dx-sync 集計・Admin 限定）を追加

### 2026-08-12 — Phase 1 中核機能（SSO/パスワードリセット/ごみ箱/ページネーション/通知/権限棚卸し/オフサイトバックアップ）

- **OIDC SSO（Entra ID / HENNGE）**: 認可コード + PKCE フロー（`GET /auth/oidc/login` → `GET /auth/oidc/callback`）。JWKS 署名・issuer/audience/nonce 検証、自動プロビジョニング、state httpOnly cookie。MFA は IdP（Conditional Access）で強制。設定手順: `docs/deployment/oidc-sso-setup.md`
- **パスワード再設定**: 自己申請（トークン SHA-256 + 60分期限）と管理者再設定（`POST /users/{id}/password-reset`）。ログイン画面に申請ダイアログ、ユーザー管理に再設定ボタン
- **ごみ箱と復元**: `GET /documents/trash` / `POST /documents/{id}/restore` と UI（一覧から除外・復元可能）
- **サーバーサイドページネーション**: `GET /documents/?include_meta=true` と UI ページャー
- **通知センター**: `notifications` テーブル + API（一覧/未読数/既読化）。ワークフロー作成・次承認者・完了/却下時に自動通知。WebUI ベル（30秒ポーリング）
- **権限棚卸し**: `GET /users/permissions-report`（JSON/CSV、admin のみ・監査記録あり）+ WebUI ボタン
- **GET 系監査**: 文書ダウンロードを `document.downloaded` としてハッシュチェーン監査ログへ記録
- **PostgreSQL 全文検索**: FTS5 に加え PG では `search_vector`（tsvector + GIN）に対応（migration `j1k2l3m4n5o6`）
- **オフサイトバックアップ**: `scripts/backup-offsite.sh`（rclone→R2/S3）+ systemd timer（毎日03:00 JST）
- **セッション管理**: WebUI の 30 分アイドルタイムアウト（自動ログアウト）
- **E2E 拡充**: Playwright 3→6 件（通知バッジ・ページネーション・SSO/パスワード再設定画面）
- **テスト**: 674 件体制（backend 400・frontend 268・playwright 6）

### 2026-08-12 — 本番運用前総合評価とセキュリティ強化（PR #120/#121/#122）

- **セキュリティ（#122）**:
  - RBAC 境界の一元化（`services/access_control.py`）— 文書/プロジェクト/ワークフロー/リビジョン/Editor/電子納品/検索/AI/統計/組織メンバーに組織・プロジェクト所属＋ロール制御。未許可は 404
  - refresh token の API 利用を拒否（access/refresh の type 検証）
  - 本番（DEBUG=false）で `SECRET_KEY` / `TIMESTAMP_HMAC_KEY` 既定値なら起動失敗（fail-fast）
  - M365 非対話ログインを既定拒否化（`M365_ALLOWED_NETWORKS` 必須・`TRUST_PROXY_HEADERS` で X-Forwarded-For 制御）
  - アップロード: PDF マジックバイト検証・プロジェクト所属検証・ストリーミング保存・filename サニタイズ
  - 文書削除を論理削除化（`deletion_requested_at` + archived。物理削除は GDPR バッチへ委譲）
  - 承認ワークフローの順序強制（後続ステップ先行承認は 409）
  - 監査ログ DB 永続化（ログイン/パスワード/文書/ユーザー/プロジェクト/ワークフロー/組織/AI 操作をハッシュチェーン付きで記録）
  - ログイン失敗 5 回で 15 分ロック（Alembic `i1j2k3l4m5n6`）＋管理者 unlock
  - パスワード 8 文字以上＋文字種 2 種以上を強制
  - ユーザー削除の FK ガード・Editor sidecar 2MB 上限・組織メンバー一覧を管理者限定
- **フロントエンド UX/アクセシビリティ（#120）**:
  - 401 リフレッシュの単一フライト化と失敗時クリーンアップ
  - 破壊的操作（文書/プロジェクト削除・ユーザー無効化）の確認ダイアログ
  - モーダルの role/aria-labelledby/Escape/フォーカストラップ（共通フック `useModalDialog`）
  - フォーム label/autoComplete/role=alert、テーブル th scope・横スクロール対応
  - PDF プレビュー iframe sandbox、デモ通知・虚構データの除去、再試行バナー
- **運用・文書・CI（#121）**:
  - Neon/PostgreSQL 移行ガイド・秘密鍵ローテーション手順（`docs/deployment/`）
  - `VERSION`（0.8.0）一元化＋`scripts/verify-version-sync.sh`
  - API リファレンス・WebUI 画面一覧・tech-stack を実装と同期
  - CI に gitleaks・npm audit・ops-checks（bash -n/shellcheck/version sync）・カバレッジ閾値 80% を追加
  - systemd ユニットの `%h` 展開・backup/restore スクリプトの安全ガード
- **テスト**: 657 件体制（backend 388・frontend 266・playwright 3）

### 2026-08-06 — Production Hardening（本番運用可能化）

- **マイグレーション修理（Issue #109）**: `alembic upgrade head` を新規 DB・既存 DB（create_all 由来）・部分適用状態で冪等化。`audit_logs` の正規作成、`ai_settings` の migration 追加、PostgreSQL `ALTER TYPE` の `autocommit_block` 化
- **CI**: SQLite + PostgreSQL の fresh upgrade とモデル完全一致検証ジョブ（`backend-migrations`）を追加
- **デプロイ**: systemd `ExecStartPre=alembic upgrade head` を復活し本番適用済み
- **セキュリティ**: API と HTML（vite dev/preview）双方に CSP / HSTS / nosniff / X-Frame-Options / Referrer-Policy / Permissions-Policy を付与。AuditMiddleware が Bearer トークンから user_id を記録
- **依存関係**: `react-router@8.3.0` / `axios@1.19.0` へ更新し npm audit 0 を再達成
- **運用**: 日次バックアップ（SQLite online backup + uploads + env、14 日保持・systemd timer）、ヘルスチェックスクリプト、運用 Runbook（`docs/operations/runbook.md`）を追加
- **監視/アラート**: 5 分毎ヘルスチェック（systemd timer）＋障害/復旧のメール通知（msmtp・30 分スロットル）。四半期毎のバックアップ復元訓練（`scripts/restore-drill.sh`）を追加し、初回訓練 PASS
- **テスト**: 633 件体制（backend 351・integration 20・frontend 259・playwright 3）

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
