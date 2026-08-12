# 🐘 SQLite → Neon/PostgreSQL 移行ガイド — CivilPDF-DX

> **2026-08-12 に本番移行完了**。それ以前は SQLite（`src/console/backend/civilpdf_dev.db`）で
> 稼働していました。本ガイドは移行手順・実施記録・ロールバックをまとめます。

## 1. 移行前の前提

| 項目 | 内容 |
|---|---|
| 対象 | 本番 SQLite → Neon PostgreSQL（または任意の PostgreSQL 16） |
| 必要な権限 | Neon プロジェクト作成権限、本番ホストのシェル、`civilpdf.env` 更新権限 |
| 作業時間 | ダウンタイム 30 分〜数時間（データ量・検証時間による） |
| 事前バックアップ | SQLite・uploads・`civilpdf.env` の完全バックアップ |
| 前提実装 | 全文検索（SQLite FTS5）は PostgreSQL でそのまま使えないため、`/api/v1/search/*` の代替実装（tsvector 等）が必要 |

## 2. 事前チェックリスト

- [x] `scripts/backup-production.sh` で最新バックアップ取得成功（2026-08-12）
- [x] アップロードファイルの件数・容量を記録
- [x] Neon プロジェクトを作成し、接続文字列を取得（`civilpdf-dx-production`）
- [x] テスト用 PostgreSQL で Alembic マイグレーションが通ることを確認（CI の `backend-migrations` ジョブで検証済み）
- [x] 移行専用のメンテナンス窓口とロールバック担当者を決める（本番ホスト管理者）

## 3. 移行手順

### 3.1 バックアップ取得

```bash
./scripts/backup-production.sh
systemctl --user stop civilpdf-backend.service
```

### 3.2 対象 PostgreSQL のスキーマ作成

Neon の接続文字列を `DATABASE_URL` に設定して、空 DB へ Alembic を適用します。

```bash
cd src/console/backend
DATABASE_URL='postgresql://user:password@host/db?sslmode=require' \
  PYTHONPATH=. alembic upgrade head
```

### 3.3 データ移行

SQLite → PostgreSQL は単純なファイルコピーでは移行できません。SQLAlchemy を使った変換スクリプトが必要です。

最低限の考慮点:

- 主キー・外部キー・enum 文字列・日時（UTC）を変換
- SQLite の `AUTOINCREMENT` と PostgreSQL の `IDENTITY` / `SEQUENCE` の整合
- `documents_fts`（SQLite FTS5 仮想テーブル）は PostgreSQL へ移行しない
- 監査ログのハッシュチェーンはレコード順を保って再投入する

実装済みの変換スクリプトを使用します（SQLAlchemy ベースの汎用スクリプト。
日時/Boolean/JSON 変換・整数 PK のシーケンス同期・行数検証を内包）:

```bash
set -a && . ~/.config/civilpdf/civilpdf.env && set +a
python3 scripts/migrate-sqlite-to-neon.py \
  --sqlite src/console/backend/civilpdf_dev.db [--verify-only]
```

### 3.4 検証

移行後、以下を確認します。

```bash
# テーブル数・行数が SQLite と一致すること
# 監査チェーン検証: GET /api/v1/audit-logs/verify が chain_valid=true
# 主要フロー: ログイン → 文書一覧 → ダウンロード → 承認
./scripts/healthcheck-civilpdf.sh
```

CI の `backend-migrations` ジョブが PostgreSQL のスキーマ整合（モデルと DB の差分ゼロ）を検証済みです。

### 3.5 接続切替

`~/.config/civilpdf/civilpdf.env` の `DATABASE_URL` を Neon へ変更し、backend を再起動します。

```bash
systemctl --user daemon-reload
systemctl --user start civilpdf-backend.service
./scripts/healthcheck-civilpdf.sh
```

### 3.5.1 実施記録（2026-08-12）

| 項目 | 値 |
| --- | --- |
| Neon プロジェクト | `civilpdf-dx-production`（ID: `falling-frog-80878192`・aws-ap-southeast-1・PG 18.4） |
| DB / ロール | `civildx` / `civildx_owner` |
| スキーマ | `alembic upgrade head` → `k1l2m3n4o5p6` |
| データ移行 | `scripts/migrate-sqlite-to-neon.py` 実行（users 1 行ほか全テーブル 0 行・検証 OK） |
| 接続切替 | `~/.config/civilpdf/civilpdf.env` の `DATABASE_URL` を Neon へ変更（`&` は引用符で囲む） |
| バックアップ | `scripts/backup-production.sh` を PostgreSQL 対応へ更新（pg_dump 18 自動選択・検証済み） |
| 検証 | `/health` 200・`/api/v1/stats/dx-sync` 401・frontend 200・alembic `PostgresqlImpl` |
| ロールバック用バックアップ | `~/civildx-backups/20260812T125213Z/`・`pre-dx-metrics-20260812/` |

### 3.5.2 注意点

- Neon は PG 18 のため、ローカルの `pg_dump`/`pg_restore` は **18 系**を使う
  （`/usr/lib/postgresql/18/bin/` を自動選択するよう `backup-production.sh` を更新済み）
- `DATABASE_URL` に `&`（`channel_binding=require` 等）を含む場合、env ファイルでは
  **二重引用符で囲む**（未引用だとシェルが `&` で分割し読み込まれない）

### 3.6 バックアップ運用の切替

移行後は SQLite online backup をやめ、以下へ切替えます。

| 方式 | 対象 |
|---|---|
| `pg_dump`（custom format・`backup-production.sh` が自動選択）/ Neon の Point-in-Time Recovery | データベース |
| 既存の `backup-production.sh`（または tar） | uploads と env |

> ✅ 2026-08-12 に `scripts/backup-production.sh` と `deploy/civilpdf-backup.service` を
> PostgreSQL 対応へ更新済み（daily 02:30 JST の systemd timer は継続）。

## 4. ロールバック

移行失敗時は、移行前バックアップから SQLite を復元します。

```bash
systemctl --user stop civilpdf-backend.service
cp ~/civildx-backups/<stamp>/civilpdf_dev.db src/console/backend/
cp ~/civildx-backups/<stamp>/civilpdf.env ~/.config/civilpdf/civilpdf.env
chmod 600 ~/.config/civilpdf/civilpdf.env
systemctl --user start civilpdf-backend.service
```

> ⚠️ 切替後に PostgreSQL へ書き込まれたデータは、SQLite へ戻した時点で失われます。切替後の書き込みを最小化し、必要なら差分をエクスポートしてからロールバックしてください。

または PostgreSQL バックアップから復元:

```bash
systemctl --user stop civilpdf-backend.service
pg_restore --clean --if-exists --dbname "$DATABASE_URL" ~/civildx-backups/<stamp>/civilpdf.dump
systemctl --user start civilpdf-backend.service
```

## 5. 移行後の監視・残課題

- [x] 全文検索 API の PostgreSQL 対応（tsvector 等・実装済み）
- [x] `scripts/backup-production.sh` の PostgreSQL 対応（2026-08-12）
- [x] `scripts/restore-drill.sh` の PostgreSQL 対応（2026-08-12・実ドリル合格）

> 全文検索は **実装済み**（`api/search.py` の PG 分岐: `search_vector` tsvector + GIN）。
> 本番 Neon で列・インデックスの存在を確認済み（2026-08-12）。
> 復元訓練（PostgreSQL）は Neon 一時ブランチへ `pg_restore` → alembic → /health → 認証フローまで
> **DRILL PASS** を確認済み（2026-08-12T23:47 JST）。
- [ ] `docs/operations/runbook.md` の DB 行・バックアップ節を更新
- [ ] Neon の PITR / バックアップ設定の運用確認
- [ ] 性能・接続プール（PgBouncer 等）の評価
