# CivilPDF-DX — 外部アラート通知・バックアップ復元訓練（2026-08-06 追記）

## 🎯 目的

前回最終報告で推奨した「外部アラート通知の導入」と「四半期バックアップ復元試験」を実装・初回実施する。

## ✅ 実装内容

1. **外部アラート通知**
   - `scripts/alert-notify.sh`: msmtp（既存 Gmail アカウント設定）でメール送信。`CIVILPDF_ALERT_TO` で宛先変更可
   - `scripts/monitor-civilpdf.sh`: 5 分毎のヘルスチェック実行・障害時メール通知（30 分スロットル）・復旧時通知・状態ログ（`~/.local/state/civildx-monitor/`）
   - `deploy/civilpdf-monitor.{service,timer}`: 5 分毎実行（`OnCalendar=*:0/5`）
   - 実機でテスト送信成功（kensan1969@gmail.com 宛）
2. **バックアップ復元訓練**
   - `scripts/restore-drill.sh`: 最新バックアップを一時領域に復元し、DB 整合性・alembic upgrade head・uploads 件数・backend 起動・認証フローを非破壊検証。失敗時はアラートメール送信
   - `deploy/civilpdf-restore-drill.{service,timer}`: 四半期毎（1/4/7/10 月 1 日 10:00 JST）
   - **初回訓練 PASS**（backup=20260806T001743Z、uploads 960 ファイル、alembic h4x5y6z7a8b9、認証フロー OK）
3. **文書同期**: runbook §4/§4.1、README 稼働状況、CHANGELOG、env example、install-systemd.sh、state.json

## 🧪 検証

- `alert-notify.sh --test` → 送信成功
- `monitor-civilpdf.sh` → healthy（アラートなし）
- `restore-drill.sh` → DRILL PASS
- timer: monitor（5 分毎）・backup（日次）・restore-drill（四半期）すべて有効化済み

## ⏭️ 残タスク

- Slack/Teams 等への通知拡張は `alert-notify.sh` 拡張で対応可能（現状メールのみ）
- 次回復元訓練: 2026-10-01（timer 自動実行、失敗時メール通知）
