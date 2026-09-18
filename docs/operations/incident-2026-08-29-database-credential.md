# インシデント記録: 本番 PostgreSQL 認証情報の失効による 21 日間の無音障害

**文書番号:** CPDF-INC-20260918
**記録日:** 2026-09-18
**検知:** 2026-09-18（人為的な調査による検知。監視では検知できていなかった）
**影響期間:** 2026-08-29 〜 2026-09-18（21 日間）
**重大度:** P0（本番の主要業務機能が停止／バックアップが 21 日間取得できず）

---

## 1. 事象

本番環境（`civilpdf.mirai-dx-platform.com`、Neon PostgreSQL）で、
**データベースへ接続するすべてのリクエストが HTTP 500 を返していた**。
同時に、**毎日のバックアップが 0 バイトのダンプを生成し続けていた**。

どちらも外形監視・定期監視では検知されず、監視は 21 日間「正常」を報告していた。

---

## 2. 検知の経緯

本セッションの初動分析（Local PostgreSQL / 本番構成の棚卸し）で、
systemd の `civilpdf-backup.service` が `failed` 状態であることを発見した。

```
$ systemctl --user status civilpdf-backup.service
× civilpdf-backup.service - CivilPDF-DX production backup
     Active: failed (Result: exit-code) since Thu 2026-09-17 17:33:48 JST
```

journal の原因:

```
pg_dump: エラー: "<neon-endpoint>" のサーバーへの接続に失敗しました:
ERROR:  password authentication failed for user '<db-role>'
```

> 注: 本ドキュメントは公開リポジトリに含まれるため、DB エンドポイントのホスト名は伏字にしている
> （ロール名は運用上の特定に必要なため残している。パスワード等の秘密値は一切記載しない）。
> 実値は `~/.config/civilpdf/civilpdf.env`（0600）を参照すること。

---

## 3. 影響（実測）

| # | 影響 | 証拠 |
| - | ---- | ---- |
| 1 | DB 参照／更新を伴う本番リクエストが全件 HTTP 500 | `POST /api/v1/auth/token` → `HTTP 500` |
| 2 | 外形監視は緑のまま（無音障害） | `healthcheck-civilpdf.sh`（旧版）→ `HEALTHCHECK: OK` |
| 3 | バックアップ 21 日連続失敗 | `~/civildx-backups/20260829..20260917` の `civilpdf.dump` がすべて 0 バイト |
| 4 | 最新の有効バックアップが 2026-08-28 | 鮮度 500 時間（20.8 日）。RPO 24 時間を大幅超過 |
| 5 | 保持期間 14 日の prune が 21 日間実行されず、古い世代が残存 | 失敗時の `set -e` により prune まで到達しない |

**データ消失は確認されていない。** Neon 上のデータは無傷で、認証情報のみが無効。
ただしこの 21 日間、いつでも復旧不能になり得る状態だった。

### 誤って「バックアップがある」と見えていた理由
`mkdir -p "$DEST/uploads"` を最初に実行していたため、`pg_dump` が失敗しても
`20260829T083207Z/` という**正規の名前のディレクトリが残り**、
中身は `civilpdf.dump` が 0 バイト・`uploads/` が空という状態だった。
ディレクトリ一覧では成功と区別できない。

---

## 4. 根本原因

### 4.1 直接原因
Neon のロール `civildx_owner` のパスワードが無効化・変更され、
`~/.config/civilpdf/civilpdf.env` の `DATABASE_URL` が指す認証情報と一致しなくなった。
（ファイルの mtime は 2026-08-12 のまま。ファイル側は変更されていない）

### 4.2 検知できなかった原因（本質）
1. **`/health` が DB を見ていなかった**
   `/health` は `settings` を返すだけで DB に触れないため、DB が全滅していても 200 を返す。
2. **外形監視の認証ゲート確認も DB に到達しなかった**
   `GET /api/v1/stats/` は認証依存で 401 を返すため、DB 参照前に応答が完結していた。
3. **バックアップ失敗が監視対象外だった**
   `civilpdf-backup.service` の失敗を監視する仕組みがなく、成否判定も
   「ディレクトリの有無」に依存していた。

**「プロセス生存」と「サービス提供可能」を同一視していたことが無音障害の本質。**

---

## 5. 実施した恒久対策（本 PR）

| 対策 | 内容 | 検証 |
| ---- | ---- | ---- |
| readiness 分離 | `GET /health/ready` を追加。`SELECT 1` を実行し DB 不通なら **503** | 本番 `DATABASE_URL` で実測: `/health` 200・`/health/ready` **503** |
| 監視强化 | `healthcheck-civilpdf.sh` が `/health/ready` を検査対象に追加 | 実測: 旧版 `OK` → 新版 `DEGRADED`（exit 1） |
| バックアップ鮮度監視 | 有効バックアップの鮮度を検査（既定 36 時間）。0 バイトは無効扱い | 実測: `newest valid backup is 500h old, limit 36h` で FAIL |
| バックアップのアトミック化 | 隠し `.incomplete-*` に作成し、検証後にのみ公開。失敗時は削除 | 単体テスト・手動実行で確認 |
| ダンプ検証 | 0 バイト検出＋`pg_restore --list` による復元可能性検証 | 同上 |
| prune 安全化 | 検証済み成功時のみ prune。`.incomplete-*` も回収 | 同上 |
| 起動の耐障害化 | DB 不通でもプロセスは起動し `/health/ready` で 503 を返す（クラッシュループ回避） | 単体テストで確認 |
| 接続タイムアウト | PostgreSQL 接続に `connect_timeout`（既定 5 秒）を設定し、probe のハングを防止 | 実測 1.4 秒で失敗応答 |
| 保持/GDPR 自動実行 | `run_retention_cycle` と `scripts/retention-job.py`、`civilpdf-retention.timer`（オプトイン） | Local PostgreSQL で dry-run → apply を実測 |

---

## 6. 未対応（承認が必要）

以下は**シークレット/認証情報の変更**を伴うため、本セッションでは実施していない。

| # | 作業 | 理由 |
| - | ---- | ---- |
| 1 | Neon のロール `civildx_owner` のパスワード再発行と `DATABASE_URL` 更新 | Credential 変更は承認必須。有効な値は本セッションでは入手できない |
| 2 | 更新後の backend 再起動と主要業務フローの実検証 | 上記に依存 |
| 3 | 復旧直後のオンデマンドバックアップ取得と復元訓練 | 上記に依存 |
| 4 | 外部アラート（msmtp/Gmail）の到達確認 | メール送信を伴うため承認必須 |

---

## 7. 再発防止（運用）

1. 外形監視・systemd 監視は **`/health/ready`** を参照する（`/health` は liveness 専用）
2. `civilpdf-backup.service` の失敗は `civilpdf-monitor` が検知してアラートする
   （鮮度チェックとして実装済み）
3. 「ディレクトリが存在する」を成功条件にしない。**0 バイトは失敗**として扱う
4. 認証情報のローテーション時は、ローテーション手順に
   「`/health/ready` が 200 を返すこと」を完了条件として含める

---

## 8. 教訓

- **可用性監視は「プロセス」ではなく「依存関係を含む業務到達性」を見る必要がある。**
  DB を見ない health check は、最も起きやすい障害（DB 断）を検知できない。
- **失敗が成功と同じ形で残るバックアップは、存在しないのと同じである。**
  アトミック公開とサイズ・復元可能性の検証を必須にすべき。
- **「コードとテストが存在する」は「機能している」ではない。**
  保持ポリシーは実装・単体テスト済みだったが、スケジューラ未接続のため本番で一度も動いていなかった。
- テストが SQLite のみで通る構成は本番固有の障害（ENUM ラベル欠落）を隠す。
  実際に本インシデント調査中、`documents.status` の editor 系 3 値が PostgreSQL に
  存在しない別の P0 欠陥も同時に発見した。
