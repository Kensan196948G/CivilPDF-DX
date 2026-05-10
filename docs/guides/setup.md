# セットアップガイド

## 開発環境

### 前提条件

| ソフトウェア | バージョン | 用途 |
|---|---|---|
| Node.js | >= 20.x | GUIアプリ・フロントエンド |
| Python | >= 3.11 | バックエンド |
| PostgreSQL | >= 15 | メインDB |
| Redis | >= 7 | キャッシュ・キュー |
| Tesseract | >= 5.x | OCR（日本語モデル含む） |

### Tesseract 日本語モデルのインストール

```bash
# Ubuntu / Debian
sudo apt install tesseract-ocr tesseract-ocr-jpn tesseract-ocr-jpn-vert

# Windows (Chocolatey)
choco install tesseract --params "/Languages:jpn,jpn_vert"
```

### 環境変数

`.env` ファイルをプロジェクトルートに作成（`.env.example` を参照）：

```env
DATABASE_URL=postgresql://user:pass@localhost:5432/civilpdf
REDIS_URL=redis://localhost:6379/0
AZURE_CLIENT_ID=<your-entra-id-client-id>
AZURE_TENANT_ID=<your-entra-id-tenant-id>
ANTHROPIC_API_KEY=<your-claude-api-key>
```

## 本番環境

（TODO：本番デプロイ手順を追記）
