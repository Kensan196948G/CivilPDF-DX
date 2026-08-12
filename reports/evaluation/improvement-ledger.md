# CivilPDF-DX 改善台帳（2026-08-12）

**文書番号:** CPDF-LEDGER-20260812

| ID | 分類 | 改善内容 | 重大度 | 状態 | PR | 完了基準 | 備考 |
|---|---|---|---|---|---|---|---|
| IMP-001 | セキュリティ | 文書/プロジェクト/ワークフロー/検索/AI/統計の RBAC 境界（所属プロジェクト＋所有文書） | 重大 | ✅ 完了 | #122 | 権限境界テスト17件 | services/access_control.py 一元化 |
| IMP-002 | セキュリティ | refresh token の access 利用禁止 | 重大 | ✅ 完了 | #122 | トークン種別テスト | decode_token(expected_type) |
| IMP-003 | セキュリティ | 秘密値デフォルトの本番 fail-fast | 高 | ✅ 完了 | #122 | config 検証テスト3件 | SECRET_KEY/TIMESTAMP_HMAC_KEY |
| IMP-004 | セキュリティ | M365 非対話ログイン既定拒否＋信頼プロキシ設定 | 重大 | ✅ 完了 | #122 | 未設定時503テスト | M365_ALLOWED_NETWORKS 必須化 |
| IMP-005 | セキュリティ | アップロード検証（マジックバイト・所属・ストリーミング・filename サニタイズ） | 高 | ✅ 完了 | #122 | 偽装PDF 415・所属外404 | |
| IMP-006 | データ保全 | 文書の論理削除（ごみ箱化）と物理削除バッチへの委譲 | 高 | ✅ 完了 | #122 | 削除後も取得可・一覧非表示 | UI 復元機能は Phase 1 |
| IMP-007 | 業務 | 承認ワークフローの順序強制 | 高 | ✅ 完了 | #122 | 後続ステップ先行承認409 | |
| IMP-008 | 監査 | 主要操作の DB 監査ログ（ハッシュチェーン）永続化 | 高 | ✅ 完了 | #122 | document.uploaded 等の監査テスト | ログイン・CRUD・WF・AI |
| IMP-009 | セキュリティ | ログイン失敗ロックアウト（5回/15分）＋管理者 unlock | 高 | ✅ 完了 | #122 | ロック/解除テスト | migration i1j2k3l4m5n6 |
| IMP-010 | セキュリティ | パスワードポリシー強化（8文字＋2種） | 中 | ✅ 完了 | #122 | 弱パスワード422 | |
| IMP-011 | データ保全 | ユーザー削除の FK 整合性ガード | 中 | ✅ 完了 | #122 | 文書所有時409 | 無効化を推奨 |
| IMP-012 | セキュリティ | Editor sidecar サイズ上限・リビジョン PDF 検証 | 中 | ✅ 完了 | #122 | 2MB上限413 | |
| IMP-013 | UI/UX | 401 リフレッシュ単一フライト・失敗時クリーンアップ | 高 | ✅ 完了 | #120 | 同時401テスト | |
| IMP-014 | UI/UX | 破壊的操作の確認ダイアログ | 中 | ✅ 完了 | #120 | 削除確認テスト | |
| IMP-015 | アクセシビリティ | モーダル role/フォーカストラップ/Escape/aria 整備 | 中 | ✅ 完了 | #120 | モーダルa11yテスト | |
| IMP-016 | アクセシビリティ | フォーム label/autoComplete/role=alert・テーブル th scope・横スクロール | 中 | ✅ 完了 | #120 | 266件通過 | |
| IMP-017 | UI/UX | デモ通知・虚構データの除去と再試行バナー | 中 | ✅ 完了 | #120 | 通知空状態テスト | |
| IMP-018 | セキュリティ | PDF プレビュー iframe sandbox | 中 | ✅ 完了 | #120 | sandbox テスト | |
| IMP-019 | 文書 | API リファレンスを実 OpenAPI と同期 | 中 | ✅ 完了 | #121 | 架空エンドポイント削除 | |
| IMP-020 | 文書 | WebUI 画面一覧・tech-stack を実装と同期 | 中 | ✅ 完了 | #121 | 実ファイル照合 | |
| IMP-021 | 運用 | Neon/PostgreSQL 移行ガイド・SQLite 暫定明記 | 高 | ✅ 完了（文書） | #121 | 移行手順・検証・ロールバック | 実移行は Phase 1 |
| IMP-022 | 運用 | VERSION 一元管理＋verify-version-sync.sh＋CI 検証 | 中 | ✅ 完了 | #121 | CI ops-checks | タグ v0.8.0 は未作成 |
| IMP-023 | CI | gitleaks・npm audit・ops-checks・カバレッジ閾値80% | 高 | ✅ 完了 | #121 | 12/12 success | |
| IMP-024 | 運用 | systemd ユニットの %h 展開・backup/restore 安全ガード | 中 | ✅ 完了 | #121 | shellcheck OK | |
| IMP-025 | セキュリティ運用 | 秘密鍵ローテーション手順（secret-management.md） | 中 | ✅ 完了 | #121 | 手順書 | |

## 未着手（課題化）

| ID | 分類 | 内容 | 優先度 | 対象 Phase |
|---|---|---|---|---|
| IMP-026 | 認証 | Entra ID OIDC SSO + HENNGE 連携 + MFA | P1 | Phase 1 |
| IMP-027 | 認証 | パスワードリセット・90日期限・セッション30分失効 | P1 | Phase 1 |
| IMP-028 | データ保全 | 論理削除のごみ箱 UI・復元 | P1 | Phase 1 |
| IMP-029 | DB | Neon/PostgreSQL 移行（FTS5→tsvector 等） | P1 | Phase 1 |
| IMP-030 | 性能 | サーバーサイドページネーション・インデックス | P1 | Phase 1 |
| IMP-031 | 監査 | GET 系（閲覧/ダウンロード）の DB 監査・5年保持 | P1 | Phase 1 |
| IMP-032 | 可用性 | オフサイト/クラウドバックアップ（RPO短縮） | P2 | Phase 2 |
| IMP-033 | 通知 | 承認通知・通知センター（Web Push/メール） | P2 | Phase 2 |
| IMP-034 | 帳票 | Excel/PDF 出力（一覧・監査・納品） | P2 | Phase 2 |
| IMP-035 | モバイル | PWA・オフラインキャッシュ | P2 | Phase 3 |
| IMP-036 | AI | RAG・引用/信頼度・入出力監査・予算上限・人間承認 | P2 | Phase 3 |
| IMP-037 | 連携 | SharePoint/Teams/Webhook | P3 | Phase 3 |
| IMP-038 | 土木固有 | 写真台帳・出来形XML連携・協力会社ポータル | P3 | Phase 3-4 |
