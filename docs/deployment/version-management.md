# 🔢 バージョン管理方針 — CivilPDF-DX

> アプリ表示・デプロイ設定・文書で使うバージョンの正本を一本化するための手順です。

## 正本

- リポジトリ直下の `VERSION` ファイルを正本とします（例: `0.8.0`）。
- 本番の `APP_VERSION` 環境変数は `VERSION` と一致させることを推奨します。

## 整合確認対象

| 場所 | 期待値 |
|---|---|
| `VERSION` | 正本 |
| `deploy/civilpdf.env.example` | `APP_VERSION=<VERSION>` |
| `.env.example` | `APP_VERSION=<VERSION>`（開発テンプレートも同一に） |
| `.env.prod.example` | `APP_VERSION=<VERSION>`（Docker 本番テンプレート） |
| `docs/operations/runbook.md` | 「現在 <VERSION>」の表記 |
| `state.json` | `release_version` が `v<VERSION>...` の形（ルート管理） |

## 既知のコード内デフォルト（未同期）

- `src/console/backend/config.py` の `app_version` デフォルトは `0.1.0`（開発用）
- `src/console/frontend/package.json` の `version` は `0.0.0`（npm パッケージメタデータ）

これらはアプリコード変更が必要なため、本運用文書の更新範囲では直接変更せず、`scripts/verify-version-sync.sh` が警告を出します。リリース時に各チームが同期することを推奨します。

## バージョン更新手順

1. `VERSION` を新バージョンへ更新
2. `scripts/verify-version-sync.sh` を実行し、文書・環境例の同期を確認
3. 必要な文書・環境例を更新して再実行
4. リリース時は Git tag `v<VERSION>` を付与（例: `git tag v0.8.0`）
5. `state.json` / `CHANGELOG.md` の更新（ルートが管理）

## 検証コマンド

```bash
./scripts/verify-version-sync.sh
```

CI の `ops-checks` ジョブでも実行され、不一致時は失敗します。
