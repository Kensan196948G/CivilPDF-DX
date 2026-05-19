# 🚀 Windows 11 ネイティブ展開チェックリスト — CivilPDF-DX

> **目的**: 現在 Linux (Ubuntu) ネイティブで開発中の CivilPDF-DX を、2026-05-29 (目安) に Windows 11 ネイティブ環境へ `git clone` で展開する際に必要となる情報を**事前にピックアップ・記入**しておくためのテンプレート。
>
> **使い方**: 各セクションの **`[ 記入欄 ]`** を社内環境情報で埋めてから、Windows 11 サーバで本書を参照しながらセットアップを進める。機密情報 (パスワード・client_secret 等) は本書には書かず、別途**パスワードマネージャ**または**シール封筒**で受け渡すこと。
>
> **更新日**: 2026-05-15 / **担当**: CTO / **想定展開日**: 2026-05-29

---

## 📌 0. 展開サマリ

| 項目 | 値 |
|---|---|
| 展開対象ホスト名 | `[ 記入欄: 例 CIVILPDF-PROD01 ]` |
| 用途 | `[ 開発 / ステージング / 本番 ]` |
| OS | Windows 11 Pro/Enterprise (64-bit) |
| 展開方式 | `git clone` + 手動セットアップ + NSSM サービス化 |
| 展開担当者 | `[ 記入欄: 氏名・連絡先 ]` |
| 展開予定日 | `[ 記入欄: YYYY-MM-DD ]` |

---

## 📌 1. ネットワーク情報

### 1.1 IP / サブネット / ゲートウェイ / DNS

| 項目 | 値 | 備考 |
|---|---|---|
| 展開サーバ IPv4 アドレス | `[ 記入欄: 例 192.168.10.50 ]` | 固定 IP 推奨 |
| サブネットマスク / プレフィックス | `[ 記入欄: 例 255.255.255.0 / 24 ]` | |
| デフォルトゲートウェイ | `[ 記入欄: 例 192.168.10.1 ]` | |
| プライマリ DNS | `[ 記入欄: 例 192.168.10.10 ]` | AD DC を指定すること |
| セカンダリ DNS | `[ 記入欄: 例 192.168.10.11 ]` | |
| VLAN ID (該当時) | `[ 記入欄 ]` | |
| 接続先 LAN セグメント名 | `[ 記入欄: 例 内部業務 VLAN ]` | |

### 1.2 プロキシ設定

| 項目 | 値 |
|---|---|
| HTTP プロキシ | `[ 記入欄: 例 http://proxy.example.local:8080 ]` |
| HTTPS プロキシ | `[ 記入欄 ]` |
| 認証要否 | `[ あり / なし ]` |
| プロキシ用ユーザー名 | `[ 記入欄 ]` (パスワードは別管理) |
| 例外 (no_proxy) | `[ 記入欄: 例 localhost,127.0.0.1,*.example.local ]` |
| PAC URL (該当時) | `[ 記入欄 ]` |

### 1.3 開放が必要なポート

| ポート | プロトコル | 方向 | 用途 |
|---|---|---|---|
| `8000` | TCP | Inbound | FastAPI backend (社内 LAN 限定) |
| `5181` | TCP | Inbound | React frontend (dev 公開時のみ。本番は IIS/Nginx で 80/443 配下) |
| `5432` | TCP | Outbound→DB | PostgreSQL (DB を別ホストに置く場合) |
| `443` | TCP | Outbound | Microsoft Graph API (`graph.microsoft.com`), Azure AD (`login.microsoftonline.com`) |
| `445` | TCP | Outbound | SMB (ファイルサーバ) |
| `88` | TCP/UDP | Outbound | Kerberos (AD 認証) |
| `389` | TCP/UDP | Outbound | LDAP (AD 検索) |
| `636` | TCP | Outbound | LDAPS (AD 検索 over TLS) |
| `53` | TCP/UDP | Outbound | DNS |
| `123` | UDP | Outbound | NTP |

ファイアウォール例外申請: `[ 申請済 / 未申請 / 申請 No. ]`

### 1.4 名前解決 / hosts

| 項目 | 値 |
|---|---|
| 内部 DNS 登録 FQDN | `[ 記入欄: 例 civilpdf.example.local ]` |
| 公開向け FQDN (該当時) | `[ 記入欄 ]` |
| hosts ファイル追記要否 | `[ あり / なし ]` |

---

## 📌 2. Active Directory 参加情報

### 2.1 ドメイン基本情報

| 項目 | 値 |
|---|---|
| AD ドメイン (DNS 名) | `[ 記入欄: 例 corp.example.local ]` |
| AD ドメイン (NetBIOS) | `[ 記入欄: 例 CORP ]` |
| フォレスト名 | `[ 記入欄 ]` |
| DC1 ホスト名 / IP | `[ 記入欄 ]` |
| DC2 ホスト名 / IP | `[ 記入欄 ]` |
| Kerberos KDC (通常 DC と同一) | `[ 記入欄 ]` |
| 機能レベル | `[ 記入欄: 例 Windows Server 2019 ]` |

### 2.2 参加用アカウント

| 項目 | 値 |
|---|---|
| ドメイン参加権限を持つ管理者 | `[ 記入欄: 例 corp\\domainjoin ]` |
| パスワード受け渡し方法 | `[ パスワードマネージャ / シール封筒 / その他 ]` |
| 配置先 OU (DN) | `[ 記入欄: 例 OU=Servers,OU=CivilPDF,DC=corp,DC=example,DC=local ]` |
| コンピュータ名命名規則 | `[ 記入欄: 例 CIVILPDF-<env><nn> ]` |

### 2.3 参加コマンド (記入後のサンプル)

```powershell
# 管理者 PowerShell で実行
Add-Computer `
  -DomainName "[ 2.1 DNS 名 ]" `
  -OUPath "[ 2.2 OU DN ]" `
  -NewName "[ 0. ホスト名 ]" `
  -Credential (Get-Credential "[ 2.2 管理者アカウント ]") `
  -Restart
```

### 2.4 アプリ用サービスアカウント (gMSA 推奨)

| 項目 | 値 |
|---|---|
| サービスアカウント種別 | `[ 通常ユーザー / gMSA / MSA ]` |
| sAMAccountName | `[ 記入欄: 例 svc_civilpdf$ ]` |
| 用途 | バックエンド/フロントエンドの NSSM サービス実行ユーザー |
| 「サービスとしてログオン」権限 | `[ 付与済 / 未 ]` |
| パスワード無期限 (gMSA は不要) | `[ 該当 / 非該当 ]` |

---

## 📌 3. ファイルサーバ情報

### 3.1 共有先 (PDF 永続化・バックアップ)

| 項目 | 値 |
|---|---|
| ファイルサーバ FQDN | `[ 記入欄: 例 fs01.corp.example.local ]` |
| 共有名 / UNC | `[ 記入欄: 例 \\\\fs01\\civilpdf$\\storage ]` |
| アクセス用アカウント | `[ 記入欄: 例 corp\\svc_civilpdf ]` |
| 必要なアクセス権 | `Modify` (PDF 保存・更新) |
| SMB バージョン | `[ SMB 3.0 / 3.1.1 ]` (SMB1 は禁止) |
| 暗号化 (SMB Encryption) | `[ 有効 / 無効 ]` |
| 監査ログ要否 | `[ あり / なし ]` |
| 容量見積 | `[ 記入欄: 例 1 TB ]` |
| バックアップポリシー | `[ 記入欄: 例 日次フル + 1h 増分・保持 30 日 ]` |

### 3.2 DFS / Namespace (該当時)

| 項目 | 値 |
|---|---|
| DFS Namespace ルート | `[ 記入欄 ]` |
| ターゲットフォルダ | `[ 記入欄 ]` |

### 3.3 ローカルマウント方針

- 案 A: 起動時に `New-PSDrive -Persist -Name Z -PSProvider FileSystem -Root <UNC> -Credential <svc>` でドライブレターを割当
- 案 B: アプリ設定 `STORAGE_BASE_PATH` に UNC をそのまま渡す
- 採用案: `[ A / B ]` (CTO 判断、設計時確定)

---

## 📌 4. Windows 11 前提ソフトウェア

| ソフトウェア | バージョン | インストール方法 | 確認 |
|---|---|---|---|
| Git for Windows | 2.45 以上 | `winget install Git.Git` または公式 MSI | ☐ |
| Python | 3.12.x (3.13 可) | `winget install Python.Python.3.12` | ☐ |
| Node.js | 20 LTS (22 LTS 可) | `winget install OpenJS.NodeJS.LTS` | ☐ |
| pnpm (任意) | 9.x | `npm install -g pnpm` | ☐ |
| PostgreSQL | 16 (15 可) | EDB Installer / `winget install PostgreSQL.PostgreSQL` | ☐ |
| Microsoft Visual C++ Redistributable | 2015-2022 | `winget install Microsoft.VCRedist.2015+.x64` | ☐ |
| NSSM (サービス化) | 2.24+ | `winget install NSSM.NSSM` | ☐ |
| OpenSSL (証明書作業用) | 任意 | Git for Windows 同梱版でも可 | ☐ |
| Windows ターミナル / PowerShell 7 | 任意 | `winget install Microsoft.PowerShell` | ☐ |

### 4.1 環境変数

| 変数 | 値 | スコープ |
|---|---|---|
| `HTTP_PROXY` / `HTTPS_PROXY` | `[ 1.2 参照 ]` | システム |
| `NO_PROXY` | `[ 1.2 参照 ]` | システム |
| `PYTHONUTF8` | `1` | システム (Windows 既定 cp932 回避) |
| `LANG` / `LC_ALL` | `ja_JP.UTF-8` | システム |
| `TZ` | `Asia/Tokyo` | システム |

---

## 📌 5. リポジトリ取得 (git clone)

### 5.1 認証方式

| 項目 | 値 |
|---|---|
| クローン方式 | `[ HTTPS + PAT / SSH 鍵 ]` |
| Git ホスト | `[ 記入欄: 例 github.com / GHE: git.example.local ]` |
| 組織 / リポジトリ | `kensan/CivilPDF-DX` (または社内ミラー) |
| デプロイキー / PAT 配置先 | `[ 記入欄: 例 C:\\ProgramData\\civilpdf\\secrets ]` (NTFS ACL で svc アカウントのみ参照可) |

### 5.2 クローン手順

```powershell
# 配置先 (例)
$base = "C:\Apps\CivilPDF-DX"
New-Item -ItemType Directory -Force -Path $base | Out-Null
cd $base

# プロキシ設定 (該当時)
git config --global http.proxy "$env:HTTP_PROXY"
git config --global https.proxy "$env:HTTPS_PROXY"

# クローン (例: HTTPS + PAT)
git clone https://<PAT>@github.com/kensan/CivilPDF-DX.git .
git checkout main
git pull --ff-only
```

### 5.3 改行コード / 実行属性

- `.gitattributes` 準拠。`core.autocrlf=false` 推奨 (UTF-8/LF 維持)
- `git config --global core.autocrlf false`

---

## 📌 6. アプリケーション設定ファイル

### 6.1 バックエンド `.env` 必要項目

| キー | 値 | 備考 |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg://civilpdf:<pass>@<host>:5432/civilpdf` | 6.2 参照 |
| `SECRET_KEY` | `[ 32 文字以上のランダム文字列 ]` | `python -c "import secrets;print(secrets.token_urlsafe(48))"` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `14` | |
| `STORAGE_BASE_PATH` | `[ 3 参照 / UNC or ローカル ]` | |
| `CORS_ORIGINS` | `https://[公開 FQDN]` | カンマ区切り |
| `LOG_LEVEL` | `INFO` | |
| `M365_TENANT_ID` | `[ 7.1 参照 ]` | |
| `M365_CLIENT_ID` | `[ 7.1 参照 ]` | |
| `M365_CLIENT_SECRET_ENC` | `[ Fernet 暗号化文字列 ]` | 平文を `.env` に書かない (設計書 §3 参照) |
| `M365_FERNET_KEY` | `[ Fernet キー ]` | 設定保管時の復号鍵。HSM/別ファイル保管推奨 |

### 6.2 PostgreSQL 設定

| 項目 | 値 |
|---|---|
| ホスト | `[ localhost / 別 DB ホスト ]` |
| ポート | `5432` |
| データベース名 | `civilpdf` |
| ユーザー名 | `civilpdf` |
| パスワード | `[ パスワードマネージャで管理 ]` |
| `pg_hba.conf` 認証方式 | `scram-sha-256` |
| 文字コード | `UTF8` |
| ロケール | `C` (ソート問題回避) |
| バックアップ | `[ 記入欄: pg_dump スケジュール / WAL アーカイブ ]` |

### 6.3 フロントエンド `.env`

| キー | 値 |
|---|---|
| `VITE_API_BASE_URL` | `https://[公開 FQDN]/api/v1` |
| `VITE_APP_TITLE` | `CivilPDF-DX` |

---

## 📌 7. Microsoft 365 (Entra ID) 接続情報

> **本セクションは `docs/architecture/m365-auth-design.md` と対で参照すること。**

### 7.1 Azure AD アプリ登録

| 項目 | 値 |
|---|---|
| テナント ID | `[ 記入欄: GUID ]` |
| アプリ表示名 | `CivilPDF-DX (prod)` (環境別に分ける) |
| クライアント ID (Application ID) | `[ 記入欄: GUID ]` |
| クライアントシークレット | `[ パスワードマネージャ管理 ]` |
| シークレット有効期限 | `[ 記入欄: YYYY-MM-DD ]` (180 日推奨、更新運用必須) |
| リダイレクト URI | (非対話式のため不要) |

### 7.2 API 権限 (Application permission)

| API | 権限 | 種類 | 管理者同意 |
|---|---|---|---|
| Microsoft Graph | `User.Read.All` | Application | ☐ 必須 |
| Microsoft Graph | `Directory.Read.All` | Application | ☐ (グループ参照する場合のみ) |

管理者同意 URL: `https://login.microsoftonline.com/<tenant>/adminconsent?client_id=<app>`

### 7.3 運用ルール

| 項目 | 値 |
|---|---|
| 初回ログイン時の自動プロビジョン | `[ 有効 / 無効 ]` (既定: 有効・role=viewer) |
| 既存 DB ユーザーとの紐付けキー | メールアドレス (`User.email`) |
| `entra_id` 列の更新 | 初回ログイン時に Graph レスポンスの `id` を記録 |
| ロール決定 | **CivilPDF-DX DB が真実** (M365 グループは使わない) |
| 退職者対応 | M365 側で無効化 → 次回ログイン時に 401 + DB 側 `status=inactive` 自動反映 |

---

## 📌 8. TLS / 証明書

| 項目 | 値 |
|---|---|
| 公開エンドポイント FQDN | `[ 1.4 参照 ]` |
| 証明書発行元 | `[ 社内 CA / Let's Encrypt / 商用 ]` |
| 証明書ファイル | `[ 記入欄: 配置先パス ]` |
| 秘密鍵ファイル | `[ 記入欄: 配置先パス、ACL 制限 ]` |
| 有効期限 | `[ 記入欄: YYYY-MM-DD ]` |
| リバースプロキシ | `[ IIS ARR / Nginx for Windows / Caddy ]` |
| HTTP→HTTPS リダイレクト | `[ あり / なし ]` |

---

## 📌 9. サービス化 (NSSM)

各サービスを Windows サービスとして登録する例。

### 9.1 バックエンド

```powershell
$root = "C:\Apps\CivilPDF-DX"
nssm install CivilPDF-Backend "$root\src\console\backend\.venv\Scripts\python.exe" `
  "-m" "uvicorn" "console.backend.main:app" "--host" "0.0.0.0" "--port" "8000"
nssm set CivilPDF-Backend AppDirectory "$root\src"
nssm set CivilPDF-Backend AppEnvironmentExtra `
  "PYTHONUTF8=1" "DATABASE_URL=..." # .env を AppEnvironmentExtra で渡すか EnvironmentFile を使う
nssm set CivilPDF-Backend ObjectName "[ 2.4 サービスアカウント ]" "[ パスワード ]"
nssm set CivilPDF-Backend Start SERVICE_AUTO_START
nssm start CivilPDF-Backend
```

### 9.2 フロントエンド (Vite preview / 本番は静的配信推奨)

本番は `npm run build` で生成した `dist/` を IIS / Nginx で配信。
開発・LAN 公開向けは `vite preview` を NSSM で常駐させる。

### 9.3 ログ出力先

| サービス | stdout | stderr |
|---|---|---|
| CivilPDF-Backend | `C:\Logs\civilpdf\backend.out.log` | `C:\Logs\civilpdf\backend.err.log` |
| CivilPDF-Frontend | `C:\Logs\civilpdf\frontend.out.log` | `C:\Logs\civilpdf\frontend.err.log` |

ローテーション: NSSM `AppRotateFiles=1`, `AppRotateBytes=10485760` (10 MB)

---

## 📌 10. 動作確認チェック

| # | 項目 | コマンド / 確認方法 | 結果 |
|---|---|---|---|
| 1 | バックエンド起動 | `curl http://localhost:8000/api/v1/health` | ☐ |
| 2 | DB マイグレーション | `alembic upgrade head` | ☐ |
| 3 | フロントエンド表示 | ブラウザで `https://[FQDN]` | ☐ |
| 4 | 一般ログイン | admin/password でログイン → JWT 取得 | ☐ |
| 5 | M365 非対話式ログイン | `corp@example.com` 入力 → JWT 取得 | ☐ |
| 6 | PDF アップロード | サンプル PDF を投稿 → 一覧表示 | ☐ |
| 7 | PDF プレビュー | 一覧から「プレビュー」→ iframe 表示 | ☐ |
| 8 | ファイルサーバ書込 | 共有先に PDF が保存されること | ☐ |
| 9 | AD アカウントログオン | サービスアカウントで RDP / `runas` 確認 | ☐ |
| 10 | Graph 接続 | `/api/v1/auth/m365/test-connection` が 200 | ☐ |

---

## 📌 11. 運用引継ぎ事項

| 項目 | 内容 |
|---|---|
| 監視 | `[ Zabbix / Prometheus / Windows Event Viewer ]` |
| アラート連絡先 | `[ 記入欄 ]` |
| バックアップ責任者 | `[ 記入欄 ]` |
| 復旧 RTO/RPO | `[ 記入欄 ]` |
| 証明書更新責任者 | `[ 記入欄 ]` |
| M365 シークレット更新責任者 | `[ 記入欄 ]` (180 日以内) |

---

## 📌 12. リスク・残課題

| # | リスク | 対応方針 |
|---|---|---|
| 1 | Windows ファイル名長制限 (260 文字) | `STORAGE_BASE_PATH` を短縮、UNC ルートに集約 |
| 2 | cp932 と UTF-8 混在によるログ文字化け | `PYTHONUTF8=1` 強制、NSSM の `AppStdoutCreationDisposition=4` |
| 3 | SMB 経由の I/O 性能低下 | ローカル SSD にキャッシュ + 夜間同期 |
| 4 | gMSA 利用時の Graph 通信 (アプリ層は client_secret なので独立) | gMSA はサービス実行のみ、Graph 認証は client_secret で完結 |
| 5 | client_secret 平文流出 | Fernet 暗号化 + ACL 制限 (設計書 §3) |
| 6 | 退職者 M365 無効化と DB ステータスのタイムラグ | 失敗時 401 + 即時 `status=inactive` 更新で吸収 |

---

## 📌 13. 参照ドキュメント

- [docs/architecture/m365-auth-design.md](../architecture/m365-auth-design.md) — M365 非対話式認証 設計書
- [docs/database-design.md](../database-design.md) — DB スキーマ
- [docs/requirements.md](../requirements.md) — 要件定義
- [README.md](../../README.md) — プロジェクト概要

---

**チェックリスト記入完了サイン**

| 役割 | 氏名 | 日付 |
|---|---|---|
| 記入者 | `_______________` | `_______________` |
| ネットワーク確認 | `_______________` | `_______________` |
| AD 確認 | `_______________` | `_______________` |
| セキュリティ確認 | `_______________` | `_______________` |
| CTO 承認 | `_______________` | `_______________` |
