# CivilPDF-DX 運用 Runbook

**文書番号:** CPDF-OPS-001  
**対象:** 本番ホスト（`civilpdf.mirai-dx-platform.com` / Cloudflare Tunnel + systemd user units）  
**最終更新:** 2026-08-06

---

## 1. 本番構成の一覧

| 項目 | 値 |
|---|---|
| 公開 URL | `https://civilpdf.mirai-dx-platform.com/` |
| TLS | Cloudflare（エッジで終端。オリジンは 127.0.0.1 のみバインド） |
| Backend | uvicorn `127.0.0.1:8180`（`deploy/civilpdf-backend.service`） |
| Frontend | vite preview `127.0.0.1:5182`（`deploy/civilpdf-frontend.service`、`dist/` 配信） |
| Tunnel | cloudflared（`deploy/civilpdf-cloudflared.service` / `~/.cloudflared/civilpdf-config.yml`） |
| DB | SQLite `src/console/backend/civilpdf_dev.db`（スキーマは Alembic 管理、起動前 `alembic upgrade head`） |
| アップロード | `~/civildx/uploads/` |
| 環境設定 | `~/.config/civilpdf/civilpdf.env`（git 管理外・0600） |
| バージョン | `APP_VERSION`（`~/.config/civilpdf/civilpdf.env`、現在 0.8.0） |

## 2. デプロイ手順（新リリース）

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
  - `civilpdf_dev.db`（SQLite online backup API で一貫性保証）
  - `uploads/`（アップロードファイル一式）
  - `civilpdf.env`（シークレット、0600）
- 保持: 14 日間（`scripts/backup-production.sh` 内 `RETENTION_DAYS`）
- RPO: 最大 24 時間（timer 起動に失敗した場合に備え、手動実行も可）
- RTO: 目標 30 分（復旧手順は下記）

### 復旧手順
1. `systemctl --user stop civilpdf-backend.service`
2. DB 復元: `cp ~/civildx-backups/<stamp>/civilpdf_dev.db <repo>/src/console/backend/`
3. アップロード復元: `rm -rf ~/civildx/uploads && cp -a ~/civildx-backups/<stamp>/uploads/. ~/civildx/uploads/`
4. `systemctl --user start civilpdf-backend.service`
5. `./scripts/healthcheck-civilpdf.sh` と主要機能スモーク

## 4. 監視

- 定期監視: `deploy/civilpdf-monitor.timer` が 5 分毎に `deploy/civilpdf-monitor.service` を起動し、`scripts/healthcheck-civilpdf.sh`（backend /health・frontend・公開 URL・認証ゲート）を実行
- 外部アラート: 障害検知時に `scripts/alert-notify.sh` が msmtp（Gmail）でメール通知（既定 30 分間隔のスロットリング付き）。復旧時にも 1 回通知
  - 通知先は `CIVILPDF_ALERT_TO`（`~/.config/civilpdf/civilpdf.env`）で変更可
  - 手動テスト: `./scripts/alert-notify.sh --test`
- ログ: `journalctl --user -u civilpdf-backend.service` / `-u civilpdf-frontend.service` / `-u civilpdf-cloudflared.service`
- 監査ログ: WebUI 監査ページ（`/api/v1/audit-logs`）＋ DB `audit_logs` の SHA-256 ハッシュチェーン（`/api/v1/audit-logs/verify`）
- 監視ログ: `~/.local/state/civildx-monitor/monitor.log`

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
- 証明書: Cloudflare が自動管理（更新作業不要）
- アクセス: 公開面はログイン必須。`DEBUG=false` を維持（DEV AUTH BYPASS 無効化）
- 権限棚卸し: ユーザーロール（admin / manager / engineer / viewer）は WebUI 管理画面で四半期ごとに確認推奨

## 7. 容量・予算

- 現状: DB 176KB・uploads 7.7MB 程度。SQLite は数 GB まで実用可能だが、本格運用開始時（同時利用者・文書数増加）に PostgreSQL へ移行する
- 移行パス: `docker-compose.prod.yml`（PostgreSQL 16）+ CI の PostgreSQL migration ジョブが検証済み
- 監視項目: ディスク使用量（`df -h`）、uploads サイズ、DB サイズ、エラー率（journalctl）

## 8. 既知の制約・残課題

- Issue #62: PDF Editor デスクトップ本体は別リポジトリ（CivilPDF-Editor）で開発継続
- Issue #94: 配布同期の完了報告（管理タスク）
- Issue #106: ecdsa advisory（upstream 修正待ち・CI 明示 ignore）
- 外部アラートはメール（msmtp/Gmail）のみ。Slack/Teams 等へ拡張する場合は `scripts/alert-notify.sh` を拡張
- 復元訓練は四半期 timer で自動化済み。訓練ログは `~/.local/state/civildx-drill/drill.log`
