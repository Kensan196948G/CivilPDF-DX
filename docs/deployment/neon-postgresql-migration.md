# 🐘 SQLite → Neon/PostgreSQL 移行ガイド — CivilPDF-DX

> 2026-08-12 時点の本番は SQLite（`src/console/backend/civilpdf_dev.db`）で稼働していますが、利用前提では **DB 正本は Neon PostgreSQL** です。本ガイドは移行を安全に行うための手順・バックアップ・ロールバック・検証をまとめます。

## 1. 移行前の前提

| 項目 | 内容 |
|---|---|
| 対象 | 本番 SQLite → Neon PostgreSQL（または任意の PostgreSQL 16） |
| 必要な権限 | Neon プロジェクト作成権限、本番ホストのシェル、`civilpdf.env` 更新権限 |
| 作業時間 | ダウンタイム 30 分〜数時間（データ量・検証時間による） |
| 事前バックアップ | SQLite・uploads・`civilpdf.env` の完全バックアップ |
| 前提実装 | 全文検索（SQLite FTS5）は PostgreSQL でそのまま使えないため、`/api/v1/search/*` の代替実装（tsvector 等）が必要 |

## 2. 事前チェックリスト

- [ ] `scripts/backup-production.sh` で最新バックアップ取得成功
- [ ] アップロードファイルの件数・容量を記録
- [ ] Neon プロジェクトを作成し、接続文字列を取得
- [ ] テスト用 PostgreSQL で Alembic マイグレーションが通ることを確認（CI の `backend-migrations` ジョブで検証済み）
- [ ] 移行専用のメンテナンス窓口とロールバック担当者を決める

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

例（概念コード。本番適用前に必ずテスト DB で検証）:

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from database import Base
import models

src = create_engine("sqlite:///civilpdf_dev.db")
dst = create_engine("postgresql://user:password@host/db?sslmode=require")

# スキーマは alembic upgrade head で作成済み。
# テーブル単位で SELECT → INSERT する変換スクリプトを実装し、
# ID・日時・enum の型差異を吸収する。
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

### 3.6 バックアップ運用の切替

移行後は SQLite online backup をやめ、以下へ切替えます。

| 方式 | 対象 |
|---|---|
| `pg_dump` / Neon の Point-in-Time Recovery | データベース |
| 既存の `backup-production.sh`（または tar） | uploads と env |

`deploy/civilpdf-backup.service` と `scripts/backup-production.sh` の PostgreSQL 対応は移行時に更新してください。

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

## 5. 移行後の監視・残課題

- [ ] 全文検索 API の PostgreSQL 対応（tsvector 等）
- [ ] `scripts/backup-production.sh` / `restore-drill.sh` の PostgreSQL 対応
- [ ] `docs/operations/runbook.md` の DB 行・バックアップ節を更新
- [ ] Neon の PITR / バックアップ設定の運用確認
- [ ] 性能・接続プール（PgBouncer 等）の評価
