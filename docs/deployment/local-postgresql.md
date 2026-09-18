# 🐘 本番DB運用ガイド — CivilPDF-DX

**決定（2026-09-18）**: 本番DBは**ホスト上のローカル PostgreSQL**で運用する。**Neon は廃止**した。

- 本番実体（2026-09-18 実測）: **docker compose スタックの `db` コンテナ**
  （`postgres:16-alpine`・named volume `civilpdf-dx_postgres_data`・ホストにポート未公開）
- バックアップ: `scripts/backup-production.sh`（compose モード = コンテナ内 `pg_dump`）
- ホスト直の PostgreSQL（`civildx_prod`）は**当ガイドの移設先として 2026-09-18 に構築した例**であり、
  現行本番は compose 内 DB を使う。ホスト直運用に切り替える場合の構築手順は §2 を参照
- **Neon を廃止した経緯と旧構成**は付録を参照

---

## 1. なぜ Neon を廃止したか

| 事象 | 内容 |
| --- | --- |
| 認証情報の失効 | 2026-08-29 頃から Neon のロール認証が失敗し、DB依存の本番リクエストが**全件 HTTP 500** になった（[インシデント記録](../operations/incident-2026-08-29-database-credential.md)） |
| 復旧手段の不在 | 認証情報の再発行には外部サービスの管理画面操作が必要で、ホスト側だけでは完結しない |
| バックアップの破綻 | 2026-08-29〜09-18 のバックアップが **21日間 0 バイト**。最新の有効なダンプは 2026-08-28 のもの |
| 判断 | 運用を外部サービスに依存させず、**ホスト上の PostgreSQL で完結**させる |

## 1.1 現行の本番構成（compose モード）

```text
利用者 → https://civilpdf.mirai-dx-platform.com
      → cloudflared（system unit civilpdf-dx-cloudflared.service）
      → 127.0.0.1:18970 frontend（nginx + SPA + /api/ proxy）
      → backend（uvicorn ×N・alembic upgrade head を起動時に適用）
      → db（postgres:16-alpine・named volume）
```

- 接続: compose ネットワーク内 `db:5432`（**ホストにポートを公開しない**設計）
- 認証: compose の `POSTGRES_*` 環境変数（`.env`・git管理外）
- スキーマ: backend コンテナの起動コマンドが `alembic upgrade head` を適用（冪等）

### バックアップ（compose モード・2026-09-18 実測）

```bash
./scripts/backup-production.sh
# PostgreSQL backup (docker compose): ... db -> civilpdf.dump
# PostgreSQL dump verified (42882 bytes, container+host pg_restore OK)
# Uploads archived: uploads.tar.gz（named volume を backend コンテナから tar）
# Backup complete (mode=compose)
```

検証内容:
1. **コンテナ内 `pg_restore --list`**（サーバーと同一版数のクライアント）で読めること
2. **ホストの既定 `pg_restore --list`** でも読めること（文書化された復元手順がホスト側で使うため）
3. ダンプが 1 バイト以上であること（0 バイト検出）

### 復元（本番復旧）

```bash
cd <production checkout>
docker compose -f docker-compose.prod.yml stop backend
cat ~/civildx-backups/<stamp>/civilpdf.dump | \
  docker compose -f docker-compose.prod.yml exec -T db \
  pg_restore -U civilpdf -d civilpdf --clean --if-exists --no-owner
cat ~/civildx-backups/<stamp>/uploads.tar.gz | \
  docker compose -f docker-compose.prod.yml exec -T backend tar xzf - -C /app/uploads
docker compose -f docker-compose.prod.yml start backend
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:18970/health
```

### 非破壊の復元訓練

`./scripts/restore-drill.sh` は最新バックアップを**ホスト PostgreSQL の訓練用DB**
（`civildx_drill`・peer 認証）へ復元し、①整合性 ②`alembic upgrade head` ③uploads 件数
④backend 起動 ⑤ログイン→`/auth/me`→`/projects` まで検証する（本番データには触れない）。

**2026-09-18 実測: DRILL PASS**（`o5p6q7r8s9t0` head・auth flow OK）

## 2. ホスト直 PostgreSQL の構築（参考・将来の切替用）

ホスト PostgreSQL（`localhost:5432`・クラスタ 16/main）を直接使う構成に切り替える場合。

```bash
# 1) DB を作成
createdb civildx_prod

# 2) スキーマを head まで適用
cd src/console/backend
DATABASE_URL='postgresql://kensan@/civildx_prod?host=/var/run/postgresql' \
PYTHONPATH=. python3 -m alembic upgrade head

# 3) モデルとの整合（テーブル・列の欠落がないこと）を確認
DATABASE_URL='postgresql://kensan@/civildx_prod?host=/var/run/postgresql' \
PYTHONPATH=. python3 - <<'PY'
import os
from sqlalchemy import create_engine, inspect
from database import Base
import models
insp = inspect(create_engine(os.environ["DATABASE_URL"]))
model = set(Base.metadata.tables); db = set(insp.get_table_names())
assert not (model - db), f"missing tables: {sorted(model - db)}"
for t in sorted(model & db):
    miss = set(Base.metadata.tables[t].columns.keys()) - {c["name"] for c in insp.get_columns(t)}
    assert not miss, f"{t} missing columns: {sorted(miss)}"
print("schema parity OK")
PY
```

Unix ソケット peer 認証（`postgresql://kensan@/civildx_prod?host=/var/run/postgresql`）を使うと
パスワードを env に保存せずに運用できる。

## 3. 既存バックアップからの移設（2026-09-18 に実施した手順）

Neon から直接読み出せない場合は、**最新の有効なバックアップ**から復元する。

```bash
# 1) 有効なバックアップを特定（0バイトは無効）
for d in ~/civildx-backups/*/; do
  [ -s "$d/civilpdf.dump" ] && echo "$(stat -c %s "$d/civilpdf.dump") $d"
done | sort -rn | head

# 2) 復元先を作成してリストア
createdb civildx_prod
/usr/lib/postgresql/16/bin/pg_restore --no-owner --no-privileges \
  -d civildx_prod ~/civildx-backups/20260828T083204Z/civilpdf.dump

# 3) head まで適用（復元直後は古いリビジョンのため）
cd src/console/backend
DATABASE_URL='postgresql://kensan@/civildx_prod?host=/var/run/postgresql' PYTHONPATH=. \
python3 -m alembic upgrade head
```

**実施記録（2026-09-18）**

| 項目 | 結果 |
| --- | --- |
| 復元元 | `20260828T083204Z/civilpdf.dump`（17テーブル・実データあり） |
| 復元エラー | `SET transaction_timeout` 1件のみ（PG17+ の設定。PG16 では無害） |
| リビジョン | `k1l2m3n4o5p6` → **`o5p6q7r8s9t0`** |
| schema parity | OK（17テーブル） |
| 保持されたデータ | `users` 1件（管理者・ADMIN・ACTIVE）、`audit_logs` 1件 |
| 備考 | 復元元の時点で `documents` は **0件**。`uploads/` のPDFは DB 行から参照されないテスト成果物 |

> ⚠️ **復元できないデータ**: Neon 上の 2026-08-29 以降の変更は、認証情報が失効しているため
> 復旧できません。ただし同時期は DB 書き込み自体が失敗していたため、実質的な影響は
> 「2026-08-28 17:32 以降、障害発生までの変更分」に限られます。

## 4. 🔴 pg_dump / pg_restore は **サーバーと同じメジャー**を使うこと

`scripts/pg-tools.sh` が **サーバーのメジャーバージョンに一致するクライアント**を自動選択します。

2026-09-18 の実測では、このホストの PATH が混在しており（`psql` 18 / `pg_dump` 17 /
`pg_restore` 16、サーバーは 16）、「インストール済みの最新バイナリ」を選ぶ実装では
**pg_dump 18 が書いたダンプを既定の `pg_restore` 16 が読めず**、復元手順が失敗しました:

```
pg_restore: エラー: ファイルヘッダ内のバージョン(1.16)はサポートされていません
```

**compose モードではこの問題が構造的に起きません**（コンテナ内の pg_dump/pg_restore は
サーバーと同一イメージ版数のため）。ホスト直運用時のみ pg-tools.sh の自動選択が効きます。

## 5. ロールバック

| 対象 | 手順 |
| --- | --- |
| データ | 直前のバックアップから復元（§1.1）。`backup-production.sh` は成功時のみ prune するため、直近の有効世代が残る |
| スキーマ | `alembic downgrade <revision>`。ただし**証跡保持の観点から自動では実行しない** |

## 6. 残課題

- **PITR 相当の仕組みは無い**: 世代バックアップ + 四半期の復元訓練で担保する
- バックアップは同一ホスト上のため、**オフサイト退避**（`scripts/backup-offsite.sh`）の運用確認が必要
- ホスト直 `civildx_prod` と compose 内 DB の**二重運用にならないよう注意**
  （現行本番は compose 内 DB。ホスト直は将来の切替時に使う）

---

## 付録: 旧 Neon 構成（2026-09-18 に廃止）

| 項目 | 内容 |
| --- | --- |
| サービス | Neon PostgreSQL（`civilpdf-dx-production`・aws-ap-southeast-1・PG 18.4） |
| 移行日 | 2026-08-12（SQLite → Neon） |
| 廃止理由 | 認証情報の失効（2026-08-29）により復旧不能・本番停止 |
| 現行の正本 | ホスト上のローカル PostgreSQL（compose 内 DB） |

廃止に伴い、リポジトリから Neon 固有の設定・スクリプト名を削除しました
（`scripts/migrate-sqlite-to-neon.py` → `migrate-sqlite-to-postgresql.py` など）。
`docs/architecture/CloudflareNeonGitHub自動化仕様.md` は**ワークスペース共通の中央ポリシー**
（ホストのMCP設定を含む）であり、本リポジトリのDB構成とは別の関心事のため対象外としています。
