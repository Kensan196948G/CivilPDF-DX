# CivilPDF-DX コンプライアンス設計書

**Phase 5.1 Compliance Foundation** — Loop 1 実装完了

---

## 1. 対象法規・規格

| カテゴリ | 規格・法規 | 対応状況 |
|---|---|---|
| 日本 | 電子帳簿保存法 (2022改正) | ✅ RFC 3161 タイムスタンプ + 保存期間管理 |
| 日本 | e-文書法 | ✅ 電子文書の真正性担保 (RFC 3161) |
| 日本 | 個人情報保護法 | ✅ GDPR同等の削除権・エクスポートAPI |
| 日本 | 国交省電子納品要領 | ✅ ISO 19650メタデータ対応 |
| 日本 | 公共工事品確法 | ✅ 10年保存ポリシー |
| EU | GDPR Art.7 (同意) | ✅ 追記型同意レコード |
| EU | GDPR Art.17 (削除権) | ✅ 論理削除→物理削除キュー |
| EU | GDPR Art.20 (ポータビリティ) | ✅ JSONエクスポートAPI |
| EU | NIS2指令 | ✅ ハッシュチェーン監査ログ |
| 米国 | CCPA/CPRA | ✅ 削除権・開示義務API |
| 国際 | ISO 19650 (BIM) | ✅ 文書メタデータフィールド |
| 国際 | PDF/A-3 | 🚧 Loop 2 (veraPDF統合) |

---

## 2. Loop 1 実装詳細

### 2.1 RFC 3161 タイムスタンプ基盤

**ファイル**: `src/console/backend/services/timestamp_service.py`

電子帳簿保存法・e-文書法が要求する「真正性担保」を実現するため、RFC 3161 TSA (Timestamp Authority) プロトコルを実装。

```
ファイルアップロード
  ↓
SHA-256 ハッシュ計算
  ↓
TSA エンドポイントへ TimeStampReq 送信
  ↓ (TSA利用不可の場合)
HMAC-SHA256 フォールバックトークン生成
  ↓
token_b64 + file_hash をドキュメントに保存
```

**設定**:
```env
TSA_URL=https://your-tsa-endpoint/tsa          # 省略時はHMACフォールバック
TSA_POLICY_OID=1.3.6.1.4.1.13762.3            # TSAポリシーOID
TSA_TIMEOUT_SECONDS=10
TIMESTAMP_HMAC_KEY=<strong-random-secret>       # 必須: 環境変数で設定
```

**注意**: HMAC フォールバックは内部監査目的で有効。法的に有効な RFC 3161 タイムスタンプには実際の TSA エンドポイント設定が必要。

### 2.2 保存期間ポリシーエンジン

**ファイル**: `src/console/backend/services/retention_service.py`  
**モデル**: `src/console/backend/models/retention_policy.py`

文書種別ごとに法的保存期間を自動設定:

| 文書種別 | 保存年数 | 法的根拠 |
|---|---|---|
| 会計・契約文書 | 7年 | 電子帳簿保存法 |
| 公共工事図面 | 10年 | 公共工事品確法 |
| 電子納品 | 永続 | 国交省電子納品要領 |
| 設計図書 | 10年 | 建設業法 |
| 一般文書 | 5年 | 内部規程 |
| その他 | 3年 | デフォルト |

**API**: 文書アップロード時に `apply_retention_policy()` が自動実行。

### 2.3 ハッシュチェーン監査ログ (NIS2/ISO 19650/J-SOX)

**ファイル**: `src/console/backend/services/audit_chain_service.py`

ブロックチェーンにインスパイアされたリンクドハッシュチェーンで、監査ログの改ざんを検出可能にする。

```
Genesis (0x000...0)
  ↓ SHA-256
Log #1: prev_hash=Genesis, seq=1, action=..., hash=H1
  ↓ SHA-256
Log #2: prev_hash=H1, seq=2, action=..., hash=H2
  ↓
...
```

**改ざん検出**: `GET /api/v1/audit-logs/verify` (管理者のみ)

```json
{
  "chain_valid": true,
  "records_checked": 1243,
  "first_broken_sequence": null,
  "error": null
}
```

**実装上の注意**: SQLite の `CURRENT_TIMESTAMP` は microseconds なし。ハッシュ計算はDB保存後の実値を使用する2フェーズコミットパターンを採用。

### 2.4 GDPR/CCPA プライバシーAPI

**ファイル**: `src/console/backend/api/privacy.py`

| エンドポイント | メソッド | 説明 | 権限 |
|---|---|---|---|
| `/api/v1/privacy/users/{id}/data` | DELETE | 削除権 (Art.17/CCPA) | Admin |
| `/api/v1/privacy/users/{id}/export` | GET | データポータビリティ (Art.20) | Admin または本人 |
| `/api/v1/privacy/consent` | POST | 同意記録 (Art.7) | 認証済み |
| `/api/v1/privacy/consent/{user_id}` | GET | 同意状況確認 | Admin または本人 |

**設計原則**:
- 削除権: 論理削除 (`deletion_requested_at` フラグ) → 猶予期間後に物理削除ジョブが実行
- 監査ログは削除されない (法的証跡保持義務)
- 同意レコードは追記のみ (revocation = granted=False の新レコード)

### 2.5 ISO 19650 メタデータ

文書モデルに ISO 19650 フィールドを追加:

| フィールド | 説明 | 例 |
|---|---|---|
| `iso19650_originator` | 作成組織コード | `XXX` |
| `iso19650_functional_breakdown` | 機能分類 | `ST` (構造) |
| `iso19650_form` | 文書形式 | `M3` (3Dモデル) |
| `iso19650_discipline` | 工種 | `AR` (建築) |
| `iso19650_number` | 連番 | `0001` |

---

## 3. データモデル追加

### ConsentRecord (同意管理)

```sql
TABLE consent_records (
  id            TEXT PRIMARY KEY,
  user_id       TEXT NOT NULL REFERENCES users(id),
  consent_type  TEXT NOT NULL,  -- analytics, marketing, third_party_sharing, ...
  version       TEXT NOT NULL DEFAULT '1.0',
  granted       BOOLEAN NOT NULL,
  ip_address    TEXT,
  user_agent    TEXT,
  source        TEXT,           -- web, api, email, ...
  disclosed_purpose         TEXT,
  disclosed_retention_period TEXT,
  disclosed_third_parties   TEXT,
  created_at    TIMESTAMP WITH TIME ZONE
)
```

### RetentionPolicy (保存期間ポリシー)

```sql
TABLE retention_policies (
  id               TEXT PRIMARY KEY,
  name             TEXT NOT NULL UNIQUE,
  category         TEXT NOT NULL,
  document_type    TEXT,
  retention_years  INTEGER NOT NULL DEFAULT 7,
  is_permanent     BOOLEAN DEFAULT FALSE,
  auto_archive     BOOLEAN DEFAULT TRUE,
  auto_delete      BOOLEAN DEFAULT FALSE,
  archive_grace_days INTEGER DEFAULT 30,
  legal_basis      TEXT,
  notes            TEXT,
  created_at       TIMESTAMP,
  updated_at       TIMESTAMP
)
```

---

## 4. セキュリティ考慮事項

- `TIMESTAMP_HMAC_KEY` は必ず環境変数で設定。コードへのハードコード禁止
- TSA 通信は HTTPS のみ使用
- プライバシーAPI の操作はすべて監査ログ (ハッシュチェーン) に記録
- 削除権行使後も監査証跡は保持 (日本法の証跡保持義務に準拠)

---

## 5. 未完了 (Loop 2 予定)

| 機能 | 対応法規 | 優先度 |
|---|---|---|
| PDF/A-3 バリデーション (veraPDF) | ISO 19005-3 | HIGH |
| フロントエンド プライバシー管理画面 | GDPR UX要件 | HIGH |
| 同意管理UI | GDPR Art.7 | HIGH |
| 文書一覧の保存期限警告バッジ | 電子帳簿保存法 | MEDIUM |
| ISO 19650 メタデータ入力フォーム | 国交省電子納品要領 | MEDIUM |
| 物理削除バックグラウンドジョブ | GDPR Art.17 | MEDIUM |

---

*Generated: Phase 5.1 Loop 1 — 2026-05-16*
