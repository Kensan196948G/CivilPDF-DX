# CivilPDF-DX テスト証跡（2026-08-12）

**文書番号:** CPDF-TEST-20260812

## 1. 実行環境

- Python 3.12.3 / Node v25.2.1 / npm 11.6.2
- ローカル実測 + GitHub Actions（main ブランチ・PR CI）

## 2. テスト実行結果

| 対象 | 改善前 | 改善後 | 実行場所 | 状態 |
|---|---:|---:|---|---|
| backend console 単体 | 351 passed | 351 + 17（security）= 368 passed | ローカル | ✅ |
| backend integration | 20 passed | 20 passed | ローカル | ✅ |
| backend 合計 | 371 | 388 | ローカル | ✅ |
| frontend vitest | 259 passed | 266 passed | ローカル | ✅ |
| frontend lint | 0 error | 0 error | ローカル | ✅ |
| frontend build | success | success | ローカル | ✅ |
| Playwright E2E | 3 passed | 3 passed | CI（Frontend E2E） | ✅ |
| **合計** | **633** | **657** | — | ✅ |
| ruff check / format | OK | OK | ローカル | ✅ |
| pip-audit | 0 critical（ecdsa PYSEC-2026-1325 は ignore 管理） | 同左 | CI | ✅ |
| npm audit | 0 vulnerabilities | 0 vulnerabilities | CI（#121 追加） | ✅ |
| gitleaks | 未実施 | no leaks found | CI（#121 追加） | ✅ |
| bash -n / shellcheck | — | OK | CI ops-checks | ✅ |
| Alembic migration（SQLite/PostgreSQL fresh） | OK | OK（新規 i1j2k3l4m5n6 含む） | CI Backend Migrations | ✅ |
| カバレッジ | 98%（主張） | 80% 閾値以上（CI ゲート） | CI | ✅ |

## 3. PR CI 結果

| PR | ジョブ | 結果 |
|---|---|---|
| #120（frontend） | 10 ジョブ | ✅ 全 success（2026-08-12 07:16Z） |
| #121（ops/docs/CI） | 12 ジョブ | ✅ 全 success（2026-08-12） |
| #122（security） | 検証中 | ローカル全テスト通過後 push |

## 4. 主要検証シナリオ（追加17件）

- 権限境界: viewer に他プロジェクト文書が非表示 / download 404 / 所属外アップロード404 / メンバーエンジニアは閲覧可
- トークン: refresh token での API アクセス 401
- アップロード: 非 PDF マジックバイト 415 / filename ヘッダーインジェクション抑止
- 論理削除: DELETE 204 → GET 200（deletion_requested_at）・一覧から除外
- ワークフロー: 後続ステップ先行承認 409
- ロックアウト: 5回失敗→403 ロック→admin unlock→再ログイン 200
- パスワード: 弱パスワード 422 / 強パスワード 201
- 監査: document.uploaded / user.created / auth.login_success が DB 監査ログに永続化
- 設定検証: 既定 SECRET_KEY / TIMESTAMP_HMAC_KEY で起動時 RuntimeError

## 5. 復旧・運用検証

- バックアップ: scripts/backup-production.sh（SQLite online backup + integrity check + 14日保持）bash -n OK
- 復元訓練: 四半期 timer + restore-drill.sh（本番データ非破壊）。2026-08-06 PASS 実績
- ヘルスチェック: 5分毎（backend/frontend/公開URL/認証ゲート）+ メールアラート
- スモーク: 本番デプロイ後 `healthcheck-civilpdf.sh` を実行する手順を Runbook に明記

## 6. 残テスト課題

- 権限境界・異常系 E2E（Playwright）の拡充（現在3件）
- 復旧（restore）の自動E2E（四半期訓練は実績あり）
- PostgreSQL/Neon 実環境での移行テスト（CI は fresh DB 検証済み）
