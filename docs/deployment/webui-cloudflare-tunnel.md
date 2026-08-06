# WebUI 公開ランブック — civilpdf.mirai-dx-platform.com (Cloudflare Tunnel)

最終更新: 2026-08-04

## 📌 構成

```
ブラウザ
  → https://civilpdf.mirai-dx-platform.com   (Cloudflare edge / TLS 終端)
  → Cloudflare Tunnel (tunnel: civilpdf / a4e4326f-…)
  → vite preview 127.0.0.1:5182              (civilpdf-frontend.service)
      └ /api/* を proxy → uvicorn 127.0.0.1:8180  (civilpdf-backend.service)
```

- 3 サービスとも **systemd user unit**（`~/.config/systemd/user/`、linger 有効）。
- 両アプリポートは **127.0.0.1 bind** — 外部経路は Tunnel のみ。
- このホストは Mirai-DX 艦隊の共用サーバー。**ポート 3000 / 5181 / 8000 は他プロジェクトが使用中**のため、CivilPDF は frontend **5182** / backend **8180** を使用する（旧 README の 5181 は別プロジェクトに割当済みの陳腐化情報だった）。

## 🔧 セットアップ（新規ホスト）

```bash
# 1. トンネル作成 (要 cloudflared login 済み ~/.cloudflared/cert.pem)
cloudflared tunnel create civilpdf

# 2. config 配置 (UUID を自分の値に置換)
cp deploy/cloudflared-civilpdf-config.yml.example ~/.cloudflared/civilpdf-config.yml

# 3. DNS ルート (⚠️ 必ず UUID 指定 — 名前指定は ~/.cloudflared/config.yml
#    (デフォルト config) の tunnel に解決される既知の罠がある)
cloudflared tunnel route dns --overwrite-dns <TUNNEL_UUID> civilpdf.mirai-dx-platform.com

# 4. env とサービス
bash deploy/install-systemd.sh
$EDITOR ~/.config/civilpdf/civilpdf.env   # SECRET_KEY 等を実値に
systemctl --user start civilpdf-backend civilpdf-frontend civilpdf-cloudflared
```

## 🔑 初期管理者

- 初期シード: `admin` / メール `kensan1969@gmail.com`（ログインは**メールアドレス**で行う — `/auth/token` は email 照合）
- 初期パスワード: `~/.config/civilpdf/initial-admin-password.txt`（600）。**初回ログイン後に画面から変更すること。**

## 🔒 Cloudflare Access（Zero Trust ゲート）

API トークンが read-only のため、Access アプリはダッシュボードで作成する（艦隊の dx-atlas と同一パターン、チーム: `winter-lake-f4c9`）:

1. one.dash.cloudflare.com → Access → Applications → **Add an application** → Self-hosted
2. Application name: `CivilPDF-DX Console` / domain: `civilpdf.mirai-dx-platform.com`
3. Policy: Allow / Include → Emails → `kensan1969@gmail.com`（必要に応じて追加）
4. 保存後、`https://civilpdf.mirai-dx-platform.com` へのアクセスが
   `winter-lake-f4c9.cloudflareaccess.com` のログインへ 302 することを確認

## ⚠️ 既知の注意点

- **vite preview の allowedHosts**: FQDN は `vite.config.ts` の `preview.allowedHosts` に列挙が必要（無いと vite 自身が 403 を返す）。
- **alembic**: `alembic upgrade head` は新規 DB・既存 DB（create_all 由来・部分適用状態含む）で冪等に実行できる（Issue #109 修理済み）。バックエンドは起動前に Alembic を適用する（systemd の ExecStartPre / docker compose の command）。`create_all` は補助経路として残る。
- **DEV AUTH BYPASS**: `DEBUG=true` で全リクエストが dev-admin になる。公開環境の env は必ず `DEBUG=false`。

## ↩️ ロールバック（完全撤去）

```bash
systemctl --user disable --now civilpdf-cloudflared civilpdf-frontend civilpdf-backend
cloudflared tunnel route dns 一覧は dash.cloudflare.com の DNS で civilpdf レコードを削除
cloudflared tunnel delete civilpdf   # 接続停止後
```
