# CivilPDF-DX

建設・土木業向けPDF業務管理プラットフォーム。GUIアプリ（exe）＋ WebUI管理コンソールの2層構成。

## Quick Facts

- **Project**: CivilPDF-DX
- **App**: Electron or Tauri（Windows exe）+ TypeScript
- **Console Frontend**: React + TypeScript + Tailwind CSS
- **Console Backend**: FastAPI (Python 3.11+)
- **DB**: PostgreSQL 15+ / Redis 7+ / SQLite（ローカル）
- **PDF Libraries**: pdf-lib, qpdf, Poppler utilities, veraPDF
- **OCR**: Tesseract (Japanese)
- **AI**: Claude API
- **Auth**: Entra ID (OIDC/SAML) + HENNGE ONE SSO
- **License**: MIT
- **Language**: コード・コメントは英語、UIラベル・ドキュメントは日本語

## Key Directories

- `src/app/` — GUIデスクトップアプリ（PDF閲覧・編集・注釈・OCR・電子印鑑）
- `src/app/core/` — PDF処理エンジン
- `src/app/ui/` — UIコンポーネント
- `src/app/pdf/` — PDF操作（結合・分割・変換・注釈・PDF/A）
- `src/app/ocr/` — OCR処理
- `src/app/stamps/` — 電子印鑑（承認印・確認印・日付印）
- `src/app/sync/` — オフライン同期エージェント
- `src/app/auth/` — Entra ID / HENNGE ONE 認証
- `src/console/frontend/` — 管理コンソールUI（React）
- `src/console/backend/` — 管理コンソールAPI（FastAPI）
- `src/console/backend/api/` — APIエンドポイント
- `src/console/backend/models/` — DBモデル（SQLAlchemy）
- `src/console/backend/services/` — ビジネスロジック
- `src/shared/` — アプリ・コンソール共通の型定義・ユーティリティ
- `tests/` — テスト（app / console / integration）
- `docs/` — ドキュメント（architecture / api / guides）
- `assets/` — アイコン・テンプレート・印鑑画像
- `.claude/skills/` — Claude Code カスタムスキル

## Common Commands

```bash
# Console backend
cd src/console/backend
uvicorn main:app --reload --port 8000
pytest tests/console/ -v

# Console frontend
cd src/console/frontend
npm run dev
npm run test
npm run lint
npm run build

# GUI app
cd src/app
npm run dev
npm run test
npm run build
npm run package        # exe生成

# Full test
npm run test:all

# Lint
npm run lint:fix
```

## Code Style

- TypeScript: strict mode, named exports only, no `any`（use `unknown`）
- Python: PEP 8, type hints required, 100 char line limit
- React: functional components + hooks only, no class components
- API: RESTful, snake_case for endpoints, camelCase for JSON response
- DB models: snake_case for columns
- Commit messages: Conventional Commits（`feat:`, `fix:`, `docs:`, `refactor:`, `test:`）
- Branch naming: `feature/`, `fix/`, `docs/`, `refactor/`

## Prohibited

- No `any` types in TypeScript
- No `console.log` for debugging（use logger）
- No hardcoded credentials or secrets
- No direct SQL queries（use ORM）
- No GPL-licensed dependencies（MIT互換性を維持）
- No Adobe proprietary format reverse engineering
- No DRM circumvention code
- Never commit `.env` files or API keys

## Domain Knowledge

### 建設業コンテキスト
- 組織階層: 本社 → 支店 → 現場事務所 → モバイル（持ち出し）
- 電子納品: 国交省電子納品要領に準拠（PDF/A, しおり構成, ファイル命名規則）
- 承認フロー: 担当者 → 現場代理人 → 監理技術者 → 支店長 → 本社
- 協力会社: 期限付き外部アカウントで参加、限定権限
- オフライン前提: 現場は通信が不安定、SQLiteローカル保存→復帰時同期

### PDF処理の原則
- PDF/A-1b 以上を電子納品の基準とする
- OCRは Tesseract + 日本語モデル（jpn + jpn_vert）
- 電子印鑑は画像ベース（PNG透過）+ メタデータ埋め込み
- 大判図面（A0/A1）は遅延レンダリングでメモリ節約

### 認証の原則
- Entra ID が IdP（OIDC/SAML 2.0）
- HENNGE ONE が認証ゲートウェイ（MFA・デバイス制御・IP制限）
- アプリ: MSAL によるトークン取得 → API Bearer認証
- コンソール: OIDC認証 → セッション管理

## Adding a New Feature

1. `docs/` に設計ドキュメントを作成
2. `src/shared/types/` に型定義を追加
3. バックエンド: `models/` → `services/` → `api/` の順に実装
4. フロントエンド: コンポーネント → ページ → ルーティングの順に実装
5. `tests/` にユニットテスト・統合テストを追加
6. 全テストがパスすることを確認
7. PR作成 → CodeRabbit / Codex Review の指摘を対応

## Notes

- GUIアプリとコンソールは同一リポジトリ（モノレポ）で管理
- 管理コンソールAPIは `/api/v1/` プレフィックス
- 監査ログは追記専用（DELETE不可）、ハッシュチェーンで改ざん防止
- AI機能は Claude API を使用、機密文書のAI処理はポリシーで制御
- コードレビューは CodeRabbit（自動PR分析）+ Codex Review（セキュリティ）
