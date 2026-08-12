# 🔑 秘密情報の管理とローテーション — CivilPDF-DX

> 本番の秘密値は Git に保存しません。保管先は `~/.config/civilpdf/civilpdf.env`（0600）のみです。

## 対象の秘密値

| 変数 | 用途 | 生成例 |
|---|---|---|
| `SECRET_KEY` | JWT 署名鍵（HS256） | `openssl rand -hex 32` |
| `TIMESTAMP_HMAC_KEY` | ローカルタイムスタンプ署名のフォールバック鍵 | `openssl rand -hex 32` |
| `M365_FERNET_KEY` | M365 client_secret の DB 暗号化鍵 | `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `ANTHROPIC_API_KEY` | Claude API | Anthropic コンソールから発行 |
| `POSTGRES_PASSWORD` | PostgreSQL / Neon 接続パスワード | `openssl rand -hex 24` |

## 保管ルール

- `deploy/civilpdf.env.example` や `.env.example` にはダミー値のみを置き、実値は Git 管理外の `.env` / `civilpdf.env` に置きます。
- ファイル権限は 0600 とします（`install -m 600`）。
- 誤コミット防止: CI の `gitleaks` ジョブと、ローカルの `gitleaks detect --source .` を利用します。

## ローテーション手順

### 1. `SECRET_KEY`

1. 新鍵を生成: `openssl rand -hex 32`
2. `~/.config/civilpdf/civilpdf.env` の `SECRET_KEY` を更新
3. `systemctl --user restart civilpdf-backend.service`
4. 影響: 発行済み JWT はすべて無効化され、利用者は再ログインが必要
5. ロールバック: 旧 `SECRET_KEY` に戻して再起動すれば旧トークンも再び有効化されます（セキュリティ上は再ログインを推奨）

### 2. `TIMESTAMP_HMAC_KEY`

1. 新鍵を生成: `openssl rand -hex 32`
2. 既存タイムスタンプの検証方式を確認（現実装は鍵を 1 つ保持するため、旧鍵で署名済みの検証結果に影響する可能性があります）
3. 影響を確認した上で env を更新し backend を再起動
4. 鍵の世代管理（旧鍵での検証保持）が必要な場合は、実装側で鍵世代のリスト管理を導入してからローテーションしてください

### 3. `M365_FERNET_KEY`

1. 新 Fernet 鍵を生成
2. 旧鍵で暗号化された `client_secret` は新鍵では復号できなくなるため、**鍵更新後は管理 UI/API で M365 client_secret を再設定**してください
3. env を更新し backend を再起動
4. ロールバック: 旧鍵へ戻し、必要なら client_secret を再設定

### 4. `ANTHROPIC_API_KEY`

1. Anthropic コンソールで新キーを発行
2. env を更新し backend を再起動
3. 無効化前の旧キーが漏えいした場合は即時失効させてください

## 本番起動前チェック

```bash
# 既定値・ダミー値が残っていないこと
rg -n "CHANGE_ME|change-this-in-production|change-me-in-production" ~/.config/civilpdf/civilpdf.env || true

# DEBUG は false であること
rg '^DEBUG=' ~/.config/civilpdf/civilpdf.env

# 秘密値が Git に混入していないこと
gitleaks detect --source .
```

CI では `secret-scan`（gitleaks）が毎 PR 実行されます。本番起動時にも `DEBUG=false` の状態で既定の秘密値を使用した場合は fail-fast する実装がセキュリティ改善として推奨されています（バックエンドチームの修正範囲）。

## バックアップと復旧

- `scripts/backup-production.sh` は `civilpdf.env` をバックアップ先へ 0600 で保存します。
- ローテーション失敗時は、バックアップから env を復元して再起動してください。
