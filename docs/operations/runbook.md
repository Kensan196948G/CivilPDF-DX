# CivilPDF-DX 運用 Runbook

**文書番号:** CPDF-OPS-001  
**対象:** 本番ホスト（`civilpdf.mirai-dx-platform.com` / Cloudflare Tunnel + systemd user units）  
**最終更新:** 2026-08-12

---

## 1. 本番構成の一覧

| 項目 | 値 |
|---|---|
| 公開 URL | `https://civilpdf.mirai-dx-platform.com/` |
| TLS | Cloudflare（エッジで終端。オリジンは 127.0.0.1 のみバインド） |
| Backend | uvicorn `127.0.0.1:8180`（`deploy/civilpdf-backend.service`） |
| Frontend | vite preview `127.0.0.1:5182`（`deploy/civilpdf-frontend.service`、`dist/` 配信） |
| Tunnel | cloudflared（`deploy/civilpdf-cloudflared.service` / `~/.cloudflared/civilpdf-config.yml`） |
| DB | SQLite `src/console/backend/civilpdf_dev.db`（**移行までの暫定**。スキーマは Alembic 管理、起動前 `alembic upgrade head`。Neon/PostgreSQL 移行手順は [neon-postgresql-migration.md](../deployment/neon-postgresql-migration.md)） |
| アップロード | `~/civildx/uploads/` |
| 環境設定 | `~/.config/civilpdf/civilpdf.env`（git 管理外・0600） |
| バージョン | 正本はリポジトリ `VERSION`（現在 0.9.0）。`APP_VERSION`（`~/.config/civilpdf/civilpdf.env`）でデプロイ時上書き。整合検証は `scripts/verify-version-sync.sh` |

## 2. デプロイ手順（新リリース）

0. リリース前確認: `./scripts/verify-version-sync.sh` で `VERSION`・env 例・文書の整合を確認
1. バックアップ取得: `./scripts/backup-production.sh`
2. リポジトリを main の検証済み commit へ更新
3. フロントエンド再ビルド: `cd src/console/frontend && npm ci && npm run build`
4. systemd ユニット再読込・再起動:
   ```bash
   systemctl --user daemon-reload
   systemctl --user restart civilpdf-backend.service   # ExecStartPre で alembic upgrade head 実行
   systemctl --user restart civilpdf-frontend.service
   ```
5. スモークテスト: `./scripts/healthcheck-civilpdf.sh`
6. 監査ログ/エラー確認: `journalctl --user -u civilpdf-backend.service -n 100 --no-pager`

## 3. バックアップと復旧

### バックアップ
- `deploy/civilpdf-backup.timer` が毎日 02:30 JST に `deploy/civilpdf-backup.service` を起動
- 保存先: `~/civildx-backups/<UTCタイムスタンプ>/`
  - PostgreSQL/Neon 運用時: `civilpdf.dump`（`pg_dump --format=custom`）
  - SQLite 運用時: `civilpdf_dev.db`（SQLite online backup API で一貫性保証）
  - `uploads/`（アップロードファイル一式）
  - `civilpdf.env`（シークレット、0600）
- 保持: 14 日間（`scripts/backup-production.sh` 内 `RETENTION_DAYS`）
- RPO: 最大 24 時間（timer 起動に失敗した場合に備え、手動実行も可）
- RTO: 目標 30 分（復旧手順は下記）

#### バックアップの成否判定（重要）
`scripts/backup-production.sh` は次の 3 点を保証します。監視・手動確認もこの基準で行ってください。

1. **アトミック公開**: 内容は隠しディレクトリ `.incomplete-<stamp>` に作成し、ダンプ検証後にのみ公開名へリネームします。
   失敗時は `.incomplete-*` が削除されるため、**失敗した run が「バックアップがある」ように見えることはありません**。
2. **サイズ検証**: `civilpdf.dump` が 0 バイトならエラー終了します（`pg_dump` の認証失敗は 0 バイトファイルを残すため）。
3. **復元可能性検証**: `pg_restore --list` でダンプを読み直してから公開します。

そのため「ディレクトリが存在する＝バックアップ成功」ではありません。**有効なバックアップ**は
`.incomplete-*` 以外かつダンプ/DB ファイルが 1 バイト以上あるものだけです。
`scripts/healthcheck-civilpdf.sh` がこの基準で最新バックアップの鮮度（既定 36 時間）を検査します。

> 🚨 **2026-08-29〜2026-09-18 の実障害**: Neon の PostgreSQL 認証情報が無効化され、
> 毎日のバックアップが 0 バイトのダンプを生成し続けました（21 日間）。
> `/health` が DB を見ていなかったため監視は緑のままでした。詳細は
> [インシデント記録](incident-2026-08-29-database-credential.md) を参照してください。

> ⚠️ **SQLite 暫定期間**の backup は `scripts/backup-production.sh`（online backup）を使用します。
> 現在の本番は PostgreSQL/Neon（`pg_dump`）です（[移行ガイド](../deployment/neon-postgresql-migration.md) §5 バックアップ運用）。

### 復旧手順
1. `systemctl --user stop civilpdf-backend.service`
2. DB 復元: `cp ~/civildx-backups/<stamp>/civilpdf_dev.db <repo>/src/console/backend/`
3. アップロード復元: `rm -rf ~/civildx/uploads && cp -a ~/civildx-backups/<stamp>/uploads/. ~/civildx/uploads/`
4. `systemctl --user start civilpdf-backend.service`
5. `./scripts/healthcheck-civilpdf.sh` と主要機能スモーク

## 4. 監視

- 定期監視: `deploy/civilpdf-monitor.timer` が 5 分毎に `deploy/civilpdf-monitor.service` を起動し、
  `scripts/healthcheck-civilpdf.sh` を実行。検査項目は
  ① backend `/health`（プロセス生存）② **backend `/health/ready`（DB 到達性）**
  ③ frontend ④ 公開 URL ⑤ 認証ゲート ⑥ **最新バックアップの鮮度**
- **`/health` と `/health/ready` の使い分け（重要）**
  - `/health`: liveness。プロセスが応答するかだけを見る（DB には触れない）
  - `/health/ready`: readiness。`SELECT 1` を実行し、DB 不通なら **503** を返す
  - 監視・外形監視・ロードバランサは **`/health/ready`** を見ること。
    `/health` だけを見ると DB 障害を検知できない（2026-08-29 の実障害の直接原因）
- バックアップ鮮度: 有効なバックアップが `CIVILPDF_BACKUP_MAX_AGE_HOURS`（既定 36 時間）より
  古い場合に FAIL。一時的に無効化する場合は `CIVILPDF_SKIP_BACKUP_CHECK=1`
- 外部アラート: 障害検知時に `scripts/alert-notify.sh` が msmtp（Gmail）でメール通知（既定 30 分間隔のスロットリング付き）。復旧時にも 1 回通知
  - 通知先は `CIVILPDF_ALERT_TO`（`~/.config/civilpdf/civilpdf.env`）で変更可
  - 手動テスト: `./scripts/alert-notify.sh --test`
- ログ: `journalctl --user -u civilpdf-backend.service` / `-u civilpdf-frontend.service` / `-u civilpdf-cloudflared.service`
- 監査ログ: WebUI 監査ページ（`/api/v1/audit-logs`）＋ DB `audit_logs` の SHA-256 ハッシュチェーン（`/api/v1/audit-logs/verify`）
- 監視ログ: `~/.local/state/civildx-monitor/monitor.log`

### 手動確認コマンド
```bash
# DB 到達性（本番は 200、DB 障害時は 503）
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8180/health/ready
# 総合ヘルスチェック（DB + バックアップ鮮度を含む）
./scripts/healthcheck-civilpdf.sh
```

## 4.2 保持ポリシー / GDPR 削除の自動実行（オプトイン）

保持期限の超過アーカイブと、削除申請から猶予期間を過ぎた文書の物理削除は
`scripts/retention-job.py` が 1 パスで実行します。以前は管理者が
`POST /api/v1/privacy/admin/run-deletion-job` を手動で叩いた時だけ実行されており、
保持期限が実質的に機能していませんでした。

- タイマー: `deploy/civilpdf-retention.timer`（毎日 03:30 JST、バックアップの後）
- **`deploy/install-systemd.sh` はこのタイマーを自動有効化しません**（物理削除を伴うため、
  運用担当の明示的な判断で有効化する設計）
- 有効化手順:
  ```bash
  # まず必ず dry-run で対象を確認する（何も変更しない）
  python3 scripts/retention-job.py --dry-run --grace-days 30
  systemctl --user enable --now civilpdf-retention.timer
  ```
- 安全装置:
  - `--apply` を付けない限り **必ず dry-run**（タイマー誤設定で削除が走らない）
  - `--grace-days`（既定 30 日）が削除申請から物理削除までの冷却期間
  - 削除対象は「利用者が削除を申請した文書」のみ。猶予期間内の文書は対象外
  - 監査ログ本体は削除しない（法的証跡保持義務）。`gdpr_physical_deletion` を追記
  - 文書レコードは保持し `file_path` を NULL 化（監査チェーンの整合を維持）
- 実行結果: `journalctl --user -u civilpdf-retention.service`、`--json` で機械可読出力
- 手動での即時実行（管理者 API）: `POST /api/v1/privacy/admin/run-deletion-job?dry_run=true`

## 4.1 バックアップ復元訓練（四半期）

- `deploy/civilpdf-restore-drill.timer` が四半期毎（1/4/7/10 月 1 日 10:00 JST）に復元訓練を自動実行
- `scripts/restore-drill.sh` は最新バックアップを一時領域へ復元し、① DB 整合性 ② `alembic upgrade head` 適用 ③ uploads 件数 ④ backend 起動 ⑤ ログイン→`/auth/me`→`/projects` を検証（本番データには触れない）
- 失敗時はアラートメール送信＋`~/.local/state/civildx-drill/drill.log` に記録
- 手動実行: `./scripts/restore-drill.sh`

## 5. ロールバック

1. アプリロールバック: 直前リリースの commit を checkout → frontend 再ビルド → backend/frontend 再起動
2. データロールバック: バックアップから DB・uploads を復元（上記 §3）
3. マイグレーション: 今回のチェーンは冪等。破損時はバックアップ復元を優先し、`alembic downgrade` は証跡保持の観点から自動では実行しない

## 6. セキュリティ運用

- シークレット: `~/.config/civilpdf/civilpdf.env` のみ（`SECRET_KEY` / `ANTHROPIC_API_KEY` 等）。ローテーション時は値を変更後 `systemctl --user restart civilpdf-backend.service`
- 依存脆弱性: CI の `pip-audit` / `npm audit` が毎 PR 実行。ecdsa PYSEC-2026-1325 は upstream 修正待ち（Issue #106 で明示管理）
- 秘密情報の漏えい防止: CI の `gitleaks` ジョブが毎 PR 実行。ローカル確認は `gitleaks detect --source .`（[secret-management.md](../deployment/secret-management.md)）
- 鍵ローテーション: `SECRET_KEY` / `TIMESTAMP_HMAC_KEY` / `M365_FERNET_KEY` の手順は [secret-management.md](../deployment/secret-management.md) に集約
- 証明書: Cloudflare が自動管理（更新作業不要）
- アクセス: 公開面はログイン必須。`DEBUG=false` を維持（DEV AUTH BYPASS 無効化）
- 権限棚卸し: ユーザーロール（admin / manager / engineer / viewer）は WebUI 管理画面で四半期ごとに確認推奨
- OIDC SSO（Phase 1）: 設定手順は [oidc-sso-setup.md](../deployment/oidc-sso-setup.md)。MFA は Entra Conditional Access / HENNGE 側で強制
- パスワード再設定: ユーザーはログイン画面「パスワードを忘れた場合」から申請（メール送信アダプタは将来実装）。管理者は WebUI ユーザー管理 → パスワード再設定で即時対応可能
- 権限棚卸しレポート: WebUI ユーザー管理 → 「権限棚卸し CSV」、または `GET /api/v1/users/permissions-report?format=csv`（admin のみ・監査ログ記録あり）

## 7. 容量・予算

- 現状: DB 176KB・uploads 7.7MB 程度。SQLite は数 GB まで実用可能だが、本格運用開始時（同時利用者・文書数増加）に PostgreSQL へ移行する
- 移行パス: `docker-compose.prod.yml`（PostgreSQL 16）+ CI の PostgreSQL migration ジョブが検証済み。Neon を含む移行手順・ロールバック・検証は [neon-postgresql-migration.md](../deployment/neon-postgresql-migration.md)
- 監視項目: ディスク使用量（`df -h`）、uploads サイズ、DB サイズ、エラー率（journalctl）

## 7.1 オフサイトバックアップ（Phase 1）

- ローカルバックアップ（§3）に加え、rclone で Cloudflare R2 / S3 へ同期可能
- 設定: `CIVILPDF_RCLONE_REMOTE=civildx-r2:civilpdf-backups` を `~/.config/civilpdf/civilpdf.env` に追加し、`rclone config` で remote を事前作成
- 手動実行: `./scripts/backup-offsite.sh`
- systemd 常設: `deploy/civilpdf-offsite-backup.service` / `.timer`（毎日 03:00 JST）を `install-systemd.sh` と同様にリンク
- 注意: ローカルバックアップに失敗している日は同期対象から除外（最新スナップショットのみ同期）

## 8. 既知の制約・残課題

- 🚨 **本番 DB 認証情報の失効（2026-08-29〜・未解決）**: Neon のロール `civildx_owner` の
  パスワードが無効化され、DB 依存の本番機能が HTTP 500 を返している。復旧には
  Credential 変更の承認と `DATABASE_URL` 更新が必要。詳細と影響は
  [インシデント記録](incident-2026-08-29-database-credential.md) 参照
- **checkout が 2 系統に分裂している（要設計判断）**: systemd units は
  `~/Projects/Mirai-DX-Project/CivilPDF-DX`（本番稼働中）を参照している一方、
  別の作業コピー `~/Projects/Mirai-Admin-Platform/CivilPDF-DX` も存在する。
  どちらも独立した git checkout であり、**変更を一方に入れても他方には反映されない**。
  デプロイ手順（§2）の対象ディレクトリを明確にし、恒久的には専用リリースディレクトリへ
  分離することを推奨する
- **共有 checkout の制約**: 本番サービス（systemd units）と監視/訓練スクリプトはリポジトリの作業ツリー（`~/Projects/Mirai-DX-Project/CivilPDF-DX`）から起動する。別セッションが feature branch へ checkout を切り替えると、その間スクリプト/コードが一時的に不在になり、monitor timer 等が `203/EXEC` で失敗しうる（2026-08-06 に実測）。運用中は main を checkout した状態を維持し、複数セッションで並行作業する場合は `git worktree` を利用すること。恒久対策は専用リリースディレクトリへの分離（要設計判断）
- Issue #62: PDF Editor デスクトップ本体は別リポジトリ（CivilPDF-Editor）で開発継続
- Issue #94: 配布同期の完了報告（管理タスク）
- Issue #106: ecdsa advisory（upstream 修正待ち・CI 明示 ignore）
- 外部アラートはメール（msmtp/Gmail）のみ。Slack/Teams 等へ拡張する場合は `scripts/alert-notify.sh` を拡張
- 復元訓練は四半期 timer で自動化済み。訓練ログは `~/.local/state/civildx-drill/drill.log`
- バージョン: リポジトリ `VERSION` は 0.9.0。`scripts/verify-version-sync.sh` は CI で毎 PR 実行され、
  `docs/operations/runbook.md` の「現在 0.9.0」表記を含めて同期を検証する。ただし git タグ `v0.9.0` は未付与（リリース時に付与）
- CI 強化（2026-08-12）: `gitleaks`（secret scan）・`npm audit`・スクリプト構文/バージョン整合チェックを追加
- GitHub 保護: ruleset `central-auto-merge`（2026-08-15 作成）が有効で、
  12 個の必須ステータスチェック通過 + squash merge のみ + force push 禁止。
  `main` への直接 push は不可（PR 経由のみ）
