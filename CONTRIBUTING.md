# コントリビューションガイド

CivilPDF-DX へのコントリビューションを歓迎します。

## 開発環境セットアップ

### 前提条件

- Node.js >= 20.x
- Python >= 3.11
- PostgreSQL >= 15
- Redis >= 7
- Git

### 初回セットアップ

```bash
git clone https://github.com/<your-org>/CivilPDF-DX.git
cd CivilPDF-DX

# GUI アプリ
cd src/app && npm install

# 管理コンソール フロントエンド
cd ../console/frontend && npm install

# 管理コンソール バックエンド
cd ../backend && pip install -r requirements.txt
```

## 開発フロー

1. `main` ブランチから作業ブランチを作成

   ```bash
   git checkout -b feature/your-feature-name
   ```

2. ブランチ命名規則

   - `feature/` — 新機能
   - `fix/` — バグ修正
   - `docs/` — ドキュメント修正
   - `refactor/` — リファクタリング
   - `test/` — テスト追加・修正

3. コミットメッセージは Conventional Commits に従う

   ```
   feat: 写真台帳PDF生成機能を追加
   fix: 大判PDF閲覧時のメモリリークを修正
   docs: 電子納品チェッカーのAPI仕様を追加
   refactor: OCRエンジンのエラーハンドリングを改善
   test: 承認ワークフローの統合テストを追加
   ```

4. テストを実行し、すべてパスすることを確認

5. Pull Request を作成
   - PRテンプレートに従って記述
   - CodeRabbit / Codex Review の指摘に対応
   - レビュー承認後にマージ

## コーディング規約

### TypeScript

- strict mode 有効
- named export のみ（default export 禁止）
- `any` 型禁止（`unknown` を使用）
- `console.log` でのデバッグ禁止（logger を使用）

### Python

- PEP 8 準拠
- 全関数に type hints 必須
- 1行100文字以内
- SQLAlchemy ORM を使用（直接SQL禁止）

### 共通

- コード・変数名・コメントは英語
- UI表示テキスト・ドキュメントは日本語
- 秘密情報のハードコーディング禁止
- GPL系ライブラリの導入禁止（MIT互換性維持）

## ライセンス

コントリビューションは MIT License のもとで提供されます。
PR を提出することで、この条件に同意したものとみなされます。

## 質問・相談

Issue を作成するか、Discussions で質問してください。
