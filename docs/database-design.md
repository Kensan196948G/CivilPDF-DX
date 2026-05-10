# CivilPDF-DX データベース設計書

バージョン: 1.0.0
作成日: 2026-05-10
対象モデル: `src/console/backend/models/user.py`, `src/console/backend/models/document.py`

---

## 1. 概要

### 技術選定

| 項目 | 採用技術 | 理由 |
|---|---|---|
| RDBMS | PostgreSQL 15+ | JSON 型ネイティブサポート、部分インデックス、論理レプリケーション |
| ORM | SQLAlchemy 2.0 | 型安全マッピング、非同期セッション対応 |
| マイグレーション | Alembic | スキーマバージョン管理、ダウングレード対応 |
| ID 生成 | UUID v4 (String) | 分散環境でのグローバル一意性保証 |

### PK の型選択について

現行実装では `String` 型で UUID を格納している（`Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))`）。
PostgreSQL ネイティブの `UUID` 型に変換すると格納効率は向上するが、既存データとの互換性維持のため現行の `VARCHAR` ベースを踏襲する。
将来的に `UUID` 型へ移行する場合は Breaking Migration として別途計画すること。

---

## 2. ER 図

```mermaid
erDiagram
    users {
        string id PK
        string email UK
        string username UK
        string full_name
        string hashed_password "nullable"
        string role "enum: admin/manager/engineer/viewer"
        string status "enum: active/inactive/suspended"
        string entra_id UK "nullable, SSO"
        timestamptz created_at
        timestamptz updated_at "nullable"
        timestamptz last_login "nullable"
    }

    projects {
        string id PK
        string name
        string code UK "工事番号"
        string description "nullable"
        boolean is_active
        timestamptz created_at
        timestamptz updated_at "nullable"
    }

    user_projects {
        string user_id FK
        string project_id FK
    }

    documents {
        string id PK
        string title
        string document_type "enum: drawing/photo/inspection/safety/contract/report/correction/other"
        string status "enum: draft/pending_review/approved/rejected/archived"
        string filename
        string file_path
        bigint file_size
        integer page_count "nullable"
        string mime_type
        boolean is_pdfa
        string pdfa_version "nullable"
        text ocr_text "nullable"
        boolean ocr_processed
        json tags
        json extra_data
        string project_id FK
        string owner_id FK
        timestamptz created_at
        timestamptz updated_at "nullable"
    }

    document_versions {
        string id PK
        string document_id FK
        integer version_number
        string filename
        string file_path
        bigint file_size
        string change_note "nullable"
        string created_by FK
        timestamptz created_at
    }

    approval_workflows {
        string id PK
        string document_id FK UK
        string status "pending/in_progress/approved/rejected"
        timestamptz created_at
        timestamptz completed_at "nullable"
    }

    approval_steps {
        string id PK
        string workflow_id FK
        string approver_id FK
        integer order
        string status "pending/approved/rejected"
        text comment "nullable"
        timestamptz decided_at "nullable"
    }

    audit_logs {
        string id PK
        string user_id FK "nullable"
        string action
        string resource_type
        string resource_id "nullable"
        string ip_address "nullable"
        text user_agent "nullable"
        json details_json "nullable"
        timestamptz created_at
    }

    ocr_results {
        string id PK
        string document_id FK
        integer page_number
        text extracted_text
        float confidence_score "nullable"
        string ocr_engine
        timestamptz created_at
    }

    ai_analysis {
        string id PK
        string document_id FK
        string analysis_type
        json result_json
        string model_used
        timestamptz created_at
    }

    pdf_versions {
        string id PK
        string document_id FK
        integer version_number
        string file_path
        string change_summary "nullable"
        string created_by FK
        timestamptz created_at
    }

    users ||--o{ user_projects : "belongs to"
    projects ||--o{ user_projects : "has"
    users ||--o{ documents : "owns"
    projects ||--o{ documents : "contains"
    documents ||--o{ document_versions : "has"
    document_versions }o--|| users : "created_by"
    documents ||--o| approval_workflows : "has"
    approval_workflows ||--o{ approval_steps : "consists of"
    approval_steps }o--|| users : "approver"
    users ||--o{ audit_logs : "generates"
    documents ||--o{ ocr_results : "has"
    documents ||--o{ ai_analysis : "has"
    documents ||--o{ pdf_versions : "has"
    pdf_versions }o--|| users : "created_by"
```

---

## 3. テーブル定義

### 3.1 users

ユーザーアカウント。Microsoft Entra ID による SSO と内部パスワード認証の両方をサポートする。

| カラム名 | 型 | 制約 | 説明 |
|---|---|---|---|
| id | VARCHAR | PK, NOT NULL | UUID v4 文字列 |
| email | VARCHAR | UNIQUE, NOT NULL, INDEX | ログイン用メールアドレス |
| username | VARCHAR | UNIQUE, NOT NULL | 表示名・識別子 |
| full_name | VARCHAR | NOT NULL | 氏名 |
| hashed_password | VARCHAR | NULLABLE | bcrypt ハッシュ。SSO ユーザーは NULL |
| role | ENUM | NOT NULL, DEFAULT 'engineer' | admin / manager / engineer / viewer |
| status | ENUM | NOT NULL, DEFAULT 'active' | active / inactive / suspended |
| entra_id | VARCHAR | UNIQUE, NULLABLE | Microsoft Entra ID オブジェクト ID |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | 登録日時 |
| updated_at | TIMESTAMPTZ | NULLABLE | 最終更新日時（onupdate） |
| last_login | TIMESTAMPTZ | NULLABLE | 最終ログイン日時 |

ENUM 定義:
- `userrole`: `admin`, `manager`, `engineer`, `viewer`
- `userstatus`: `active`, `inactive`, `suspended`

---

### 3.2 projects

工事プロジェクト。工事番号（code）でユニーク管理される。

| カラム名 | 型 | 制約 | 説明 |
|---|---|---|---|
| id | VARCHAR | PK, NOT NULL | UUID v4 文字列 |
| name | VARCHAR | NOT NULL | プロジェクト名称 |
| code | VARCHAR | UNIQUE, NOT NULL | 工事番号（社内一意コード） |
| description | VARCHAR | NULLABLE | プロジェクト概要 |
| is_active | BOOLEAN | NOT NULL, DEFAULT TRUE | 有効フラグ |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | 登録日時 |
| updated_at | TIMESTAMPTZ | NULLABLE | 最終更新日時（onupdate） |

---

### 3.3 user_projects（中間テーブル）

users と projects の多対多関係を管理する。

| カラム名 | 型 | 制約 | 説明 |
|---|---|---|---|
| user_id | VARCHAR | FK → users.id, NOT NULL | ユーザー ID |
| project_id | VARCHAR | FK → projects.id, NOT NULL | プロジェクト ID |

複合 PK: `(user_id, project_id)`

---

### 3.4 documents

土木工事関連 PDF ドキュメントの管理テーブル。

| カラム名 | 型 | 制約 | 説明 |
|---|---|---|---|
| id | VARCHAR | PK, NOT NULL | UUID v4 文字列 |
| title | VARCHAR | NOT NULL | ドキュメントタイトル |
| document_type | ENUM | NOT NULL, DEFAULT 'other' | 書類種別（下記参照） |
| status | ENUM | NOT NULL, DEFAULT 'draft' | 承認ステータス（下記参照） |
| filename | VARCHAR | NOT NULL | 元ファイル名 |
| file_path | VARCHAR | NOT NULL | ストレージ上のパス |
| file_size | BIGINT | NOT NULL | バイト単位のファイルサイズ |
| page_count | INTEGER | NULLABLE | PDF ページ数 |
| mime_type | VARCHAR | NOT NULL, DEFAULT 'application/pdf' | MIME タイプ |
| is_pdfa | BOOLEAN | NOT NULL, DEFAULT FALSE | PDF/A 準拠フラグ |
| pdfa_version | VARCHAR | NULLABLE | 例: 'PDF/A-1b', 'PDF/A-2b' |
| ocr_text | TEXT | NULLABLE | OCR 抽出テキスト全文 |
| ocr_processed | BOOLEAN | NOT NULL, DEFAULT FALSE | OCR 処理済みフラグ |
| tags | JSON | NOT NULL, DEFAULT '[]' | タグ一覧（文字列配列） |
| extra_data | JSON | NOT NULL, DEFAULT '{}' | 拡張メタデータ（任意 KV） |
| project_id | VARCHAR | FK → projects.id, NOT NULL | 所属プロジェクト |
| owner_id | VARCHAR | FK → users.id, NOT NULL | アップロードユーザー |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | 登録日時 |
| updated_at | TIMESTAMPTZ | NULLABLE | 最終更新日時（onupdate） |

ENUM 定義:
- `documenttype`: `drawing`（図面）, `photo`（写真台帳）, `inspection`（検査記録）, `safety`（安全書類）, `contract`（契約書）, `report`（報告書）, `correction`（是正指示書）, `other`
- `documentstatus`: `draft`, `pending_review`, `approved`, `rejected`, `archived`

設計上の注意: `ocr_text` カラムは全文テキストを格納するため大きくなり得る。高頻度の全文検索が必要な場合は PostgreSQL の `tsvector` カラムと GIN インデックスの追加、または Elasticsearch への切り出しを検討する。

---

### 3.5 document_versions

ドキュメントのファイルバージョン履歴。版管理の実体はこのテーブルが持つ。

| カラム名 | 型 | 制約 | 説明 |
|---|---|---|---|
| id | VARCHAR | PK, NOT NULL | UUID v4 文字列 |
| document_id | VARCHAR | FK → documents.id, NOT NULL | 親ドキュメント |
| version_number | INTEGER | NOT NULL | 版番号（1 始まり） |
| filename | VARCHAR | NOT NULL | 当バージョンのファイル名 |
| file_path | VARCHAR | NOT NULL | ストレージ上のパス |
| file_size | BIGINT | NOT NULL | バイト単位のファイルサイズ |
| change_note | VARCHAR | NULLABLE | 変更理由・備考 |
| created_by | VARCHAR | FK → users.id, NOT NULL | 作成ユーザー |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | 作成日時 |

UNIQUE 制約: `(document_id, version_number)`

---

### 3.6 approval_workflows

ドキュメントごとの承認フロー管理。1 ドキュメントにつき 1 ワークフローのみ存在する。

| カラム名 | 型 | 制約 | 説明 |
|---|---|---|---|
| id | VARCHAR | PK, NOT NULL | UUID v4 文字列 |
| document_id | VARCHAR | FK → documents.id, UNIQUE, NOT NULL | 対象ドキュメント（1:1） |
| status | VARCHAR | NOT NULL, DEFAULT 'pending' | pending / in_progress / approved / rejected |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | 作成日時 |
| completed_at | TIMESTAMPTZ | NULLABLE | 承認完了または却下日時 |

設計上の注意: `status` カラムは現状 VARCHAR だが、将来的に ENUM 化することで整合性を強化できる。

---

### 3.7 approval_steps

承認フロー内の個別承認ステップ。`order` カラムで承認順序を制御する。

| カラム名 | 型 | 制約 | 説明 |
|---|---|---|---|
| id | VARCHAR | PK, NOT NULL | UUID v4 文字列 |
| workflow_id | VARCHAR | FK → approval_workflows.id, NOT NULL | 所属ワークフロー |
| approver_id | VARCHAR | FK → users.id, NOT NULL | 承認者ユーザー |
| order | INTEGER | NOT NULL | 承認順序（小さいほど先） |
| status | VARCHAR | NOT NULL, DEFAULT 'pending' | pending / approved / rejected |
| comment | TEXT | NULLABLE | 承認・却下コメント |
| decided_at | TIMESTAMPTZ | NULLABLE | 決定日時 |

---

### 3.8 audit_logs（新規設計）

操作監査ログ。誰が・何を・いつ操作したかを記録する。セキュリティ要件および建設業法上の監査証跡として保持する。

| カラム名 | 型 | 制約 | 説明 |
|---|---|---|---|
| id | VARCHAR | PK, NOT NULL | UUID v4 文字列 |
| user_id | VARCHAR | FK → users.id, NULLABLE | 操作ユーザー（未認証操作は NULL） |
| action | VARCHAR | NOT NULL | 操作種別（例: `document.upload`, `user.login`, `workflow.approve`） |
| resource_type | VARCHAR | NOT NULL | 対象リソース種別（例: `document`, `user`, `project`） |
| resource_id | VARCHAR | NULLABLE | 対象リソースの ID |
| ip_address | VARCHAR | NULLABLE | クライアント IP アドレス（IPv4/IPv6） |
| user_agent | TEXT | NULLABLE | HTTP User-Agent ヘッダ |
| details_json | JSON | NULLABLE | 変更前後の値など追加情報 |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | 発生日時 |

設計上の注意:
- 削除禁止。論理削除も行わない。監査ログは追記専用（INSERT ONLY）とする。
- `user_id` は FK を設定するが、ユーザー削除時に NULL とする（SET NULL）ことで監査証跡を維持する。
- パーティショニング: `created_at` で月次レンジパーティショニングを適用し、古いパーティションをアーカイブ可能にする。

---

### 3.9 ocr_results（新規設計）

ドキュメントの OCR 処理結果をページ単位で格納する。`documents.ocr_text` との役割分担は以下の通り:
- `documents.ocr_text`: 全ページ結合テキスト（検索用）
- `ocr_results`: ページ単位の詳細結果（信頼度・エンジン情報付き）

| カラム名 | 型 | 制約 | 説明 |
|---|---|---|---|
| id | VARCHAR | PK, NOT NULL | UUID v4 文字列 |
| document_id | VARCHAR | FK → documents.id, NOT NULL | 対象ドキュメント |
| page_number | INTEGER | NOT NULL | ページ番号（1 始まり） |
| extracted_text | TEXT | NOT NULL | 抽出テキスト |
| confidence_score | FLOAT | NULLABLE | 認識信頼度（0.0〜1.0） |
| ocr_engine | VARCHAR | NOT NULL | 使用 OCR エンジン（例: `google-vision`, `tesseract-5`） |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | 処理日時 |

UNIQUE 制約: `(document_id, page_number)` — 同一ドキュメントの同一ページの再処理は UPDATE または DELETE + INSERT とする。

---

### 3.10 ai_analysis（新規設計）

AI による文書解析結果。解析種別ごとに複数レコードを持てる。

| カラム名 | 型 | 制約 | 説明 |
|---|---|---|---|
| id | VARCHAR | PK, NOT NULL | UUID v4 文字列 |
| document_id | VARCHAR | FK → documents.id, NOT NULL | 対象ドキュメント |
| analysis_type | VARCHAR | NOT NULL | 解析種別（例: `classification`, `compliance_check`, `summary`） |
| result_json | JSON | NOT NULL | 解析結果（構造は analysis_type 依存） |
| model_used | VARCHAR | NOT NULL | 使用モデル（例: `gpt-4o`, `claude-3-5-sonnet`） |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | 解析実行日時 |

---

### 3.11 pdf_versions（新規設計）

PDF レンダリング済みバージョンの管理。`document_versions` がアップロードファイルの版管理であるのに対し、このテーブルはシステム生成の PDF ファイル（PDF/A 変換後、透かし付きなど）を管理する。

| カラム名 | 型 | 制約 | 説明 |
|---|---|---|---|
| id | VARCHAR | PK, NOT NULL | UUID v4 文字列 |
| document_id | VARCHAR | FK → documents.id, NOT NULL | 対象ドキュメント |
| version_number | INTEGER | NOT NULL | 版番号（1 始まり） |
| file_path | VARCHAR | NOT NULL | ストレージ上のパス |
| change_summary | VARCHAR | NULLABLE | 変更概要（例: 'PDF/A-2b 変換', '承認印押印'） |
| created_by | VARCHAR | FK → users.id, NOT NULL | 生成ユーザー（システム操作の場合はサービスアカウント ID） |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | 生成日時 |

UNIQUE 制約: `(document_id, version_number)`

---

## 4. インデックス設計

### 既存テーブル（実装済み）

| テーブル | カラム | インデックス種別 | 目的 |
|---|---|---|---|
| users | email | UNIQUE INDEX | ログイン時の検索 |

### 追加推奨インデックス

| テーブル | カラム | インデックス種別 | 目的 |
|---|---|---|---|
| documents | project_id | BTREE | プロジェクト別一覧取得（頻繁） |
| documents | owner_id | BTREE | ユーザー別ドキュメント一覧 |
| documents | status | BTREE | ステータスフィルタリング |
| documents | document_type | BTREE | 書類種別フィルタリング |
| documents | (project_id, status) | 複合 BTREE | プロジェクト内ステータス絞り込み |
| documents | ocr_processed | 部分 BTREE `WHERE ocr_processed = FALSE` | 未処理ドキュメントのバッチ取得 |
| document_versions | document_id | BTREE | バージョン一覧取得 |
| document_versions | created_by | BTREE | ユーザー別操作履歴 |
| approval_workflows | status | BTREE | 承認待ち一覧取得 |
| approval_steps | workflow_id | BTREE | ステップ一覧取得（order で sort） |
| approval_steps | approver_id | BTREE | 承認者別タスク一覧 |
| approval_steps | (approver_id, status) | 複合 BTREE | 承認者の未処理タスク取得 |
| audit_logs | user_id | BTREE | ユーザー操作履歴 |
| audit_logs | resource_type, resource_id | 複合 BTREE | リソース別監査ログ検索 |
| audit_logs | created_at | BTREE | 時刻範囲検索（パーティションキー） |
| audit_logs | action | BTREE | 操作種別集計 |
| ocr_results | document_id | BTREE | ドキュメント別 OCR 結果取得 |
| ai_analysis | document_id | BTREE | ドキュメント別解析結果取得 |
| ai_analysis | (document_id, analysis_type) | 複合 BTREE | 解析種別での絞り込み |
| pdf_versions | document_id | BTREE | ドキュメント別 PDF バージョン一覧 |
| projects | is_active | 部分 BTREE `WHERE is_active = TRUE` | アクティブプロジェクト一覧 |
| user_projects | project_id | BTREE | プロジェクトメンバー一覧 |

### 全文検索インデックス（将来対応）

`documents.ocr_text` および `ocr_results.extracted_text` への全文検索が必要になった場合:

```sql
-- documents テーブルに tsvector カラムを追加
ALTER TABLE documents ADD COLUMN ocr_text_tsv tsvector
    GENERATED ALWAYS AS (to_tsvector('japanese', coalesce(ocr_text, ''))) STORED;

CREATE INDEX idx_documents_ocr_text_tsv ON documents USING GIN (ocr_text_tsv);
```

---

## 5. 制約とリレーション

### 外部キー制約と CASCADE 設定

| 参照元テーブル | カラム | 参照先 | ON DELETE | 理由 |
|---|---|---|---|---|
| user_projects | user_id | users.id | CASCADE | ユーザー削除時に所属プロジェクト紐付けを自動削除 |
| user_projects | project_id | projects.id | CASCADE | プロジェクト削除時に所属ユーザー紐付けを自動削除 |
| documents | project_id | projects.id | RESTRICT | ドキュメントを持つプロジェクトの誤削除防止 |
| documents | owner_id | users.id | RESTRICT | アップロードユーザーの誤削除防止 |
| document_versions | document_id | documents.id | CASCADE | 親ドキュメント削除で版履歴も連動削除 |
| document_versions | created_by | users.id | RESTRICT | 作成者の誤削除防止 |
| approval_workflows | document_id | documents.id | CASCADE | 親ドキュメント削除でワークフローも連動削除 |
| approval_steps | workflow_id | approval_workflows.id | CASCADE | ワークフロー削除でステップも連動削除 |
| approval_steps | approver_id | users.id | RESTRICT | 承認者の誤削除防止 |
| audit_logs | user_id | users.id | SET NULL | ユーザー削除後も監査証跡を保持 |
| ocr_results | document_id | documents.id | CASCADE | 親ドキュメント削除で OCR 結果も連動削除 |
| ai_analysis | document_id | documents.id | CASCADE | 親ドキュメント削除で解析結果も連動削除 |
| pdf_versions | document_id | documents.id | CASCADE | 親ドキュメント削除で PDF バージョンも連動削除 |
| pdf_versions | created_by | users.id | RESTRICT | 生成ユーザーの誤削除防止 |

### UNIQUE 制約まとめ

| テーブル | カラム | 説明 |
|---|---|---|
| users | email | ログイン ID の一意性 |
| users | username | 表示名の一意性 |
| users | entra_id | SSO 識別子の一意性 |
| projects | code | 工事番号の一意性 |
| approval_workflows | document_id | 1 ドキュメント = 1 ワークフロー |
| document_versions | (document_id, version_number) | 版番号の重複防止 |
| ocr_results | (document_id, page_number) | ページ単位の OCR 結果の重複防止 |
| pdf_versions | (document_id, version_number) | PDF 版番号の重複防止 |

### CHECK 制約（推奨追加）

```sql
-- approval_steps の order は 1 以上
ALTER TABLE approval_steps ADD CONSTRAINT chk_approval_steps_order CHECK (order >= 1);

-- document_versions の version_number は 1 以上
ALTER TABLE document_versions ADD CONSTRAINT chk_document_versions_version CHECK (version_number >= 1);

-- ocr_results の confidence_score は 0.0〜1.0
ALTER TABLE ocr_results ADD CONSTRAINT chk_ocr_confidence CHECK (confidence_score IS NULL OR (confidence_score >= 0.0 AND confidence_score <= 1.0));

-- ocr_results の page_number は 1 以上
ALTER TABLE ocr_results ADD CONSTRAINT chk_ocr_page_number CHECK (page_number >= 1);

-- documents の file_size は 0 より大きい
ALTER TABLE documents ADD CONSTRAINT chk_documents_file_size CHECK (file_size > 0);
```

---

## 6. マイグレーション方針

### 基本方針

- Alembic を使用してすべてのスキーマ変更をバージョン管理する。
- `alembic upgrade head` を CI パイプラインに組み込み、デプロイと同時に自動適用する。
- 本番環境への適用前に `alembic upgrade --sql` でドライランを出力してレビューする。

### ゼロダウンタイムマイグレーションのルール

| 変更種別 | 安全な方法 | 禁止事項 |
|---|---|---|
| カラム追加 | `ALTER TABLE ADD COLUMN DEFAULT` を使用。NOT NULL 追加は段階的に行う | いきなり `NOT NULL` 制約付きの新カラムを追加（既存行がエラー） |
| カラム削除 | アプリ側で参照を削除 → デプロイ → カラム削除の 2 フェーズ | アプリが参照中のカラムをいきなり削除 |
| カラムリネーム | 新カラム追加 → データコピー → アプリ切替 → 旧カラム削除の 3 フェーズ | `ALTER TABLE RENAME COLUMN`（ダウンタイム発生） |
| インデックス追加 | `CREATE INDEX CONCURRENTLY` を使用 | 通常の `CREATE INDEX`（テーブルロック） |
| インデックス削除 | `DROP INDEX CONCURRENTLY` を使用 | 通常の `DROP INDEX` |
| ENUM 値追加 | `ALTER TYPE ... ADD VALUE` は非トランザクションのため専用マイグレーションで単独実行 | 他の DDL と同一トランザクション内で実行 |
| ENUM 値削除 | 新 ENUM 型を作成してカラムを切り替える 3 フェーズ手順 | 直接 ENUM 値を削除（依存データが残るとエラー） |
| テーブル削除 | アプリ参照を削除してデプロイ後、次のマイグレーションで削除 | アプリが参照中のテーブルをいきなり削除 |

### Alembic 運用コマンド

```bash
# マイグレーションファイルの生成
alembic revision --autogenerate -m "add audit_logs table"

# 本番適用前のドライラン（SQL 出力）
alembic upgrade head --sql > migration_preview.sql

# 適用
alembic upgrade head

# 一つ前に戻す（緊急ロールバック）
alembic downgrade -1

# 現在のリビジョン確認
alembic current

# 履歴一覧
alembic history --verbose
```

### 破壊的マイグレーションの承認フロー

1. 変更内容をプルリクエスト本文に明記する（影響テーブル・推定ロック時間・ロールバック手順）。
2. DB レビュアー（本設計書担当者）の承認を必須とする。
3. ステージング環境で `pg_dump` → マイグレーション適用 → 動作確認 → 本番適用の手順を踏む。
4. 本番適用はメンテナンス時間帯（深夜帯）に実施する。ただし CONCURRENTLY オプション使用時はダウンタイム不要。

---

## 7. データ保持ポリシー

### 監査ログ（audit_logs）

| 項目 | 方針 |
|---|---|
| 保存期間 | 最低 7 年（建設業法・電子帳簿保存法の要件に準拠） |
| 削除方法 | 月次パーティションを `DETACH PARTITION` → 別ストレージへアーカイブ → `DROP TABLE` の順で実施 |
| アクセス制限 | admin ロールのみ参照可。アプリケーション層では INSERT のみ許可、DELETE 禁止 |
| バックアップ | 日次スナップショット + WAL アーカイブで PITR（Point-in-Time Recovery）対応 |

### ドキュメントファイル（file_path 参照先）

| 項目 | 方針 |
|---|---|
| ストレージ | オブジェクトストレージ（Azure Blob Storage / AWS S3 互換）推奨 |
| バージョン保持 | `document_versions` に記録された全バージョンを保持（削除しない） |
| アーカイブ | `status = 'archived'` のドキュメントは低コストストレージ（コールドティア）へ移行 |
| 削除方針 | 論理削除のみ実施（`status = 'archived'` または `is_active = FALSE`）。物理削除は行わない |
| バックアップ | ストレージレベルで地理的冗長化（GRS）を設定 |

### OCR・AI 解析結果

| 項目 | 方針 |
|---|---|
| 保存期間 | 親ドキュメントの保存期間に準拠（CASCADE DELETE） |
| 再生成 | OCR/AI は再実行可能なため、ストレージ逼迫時は古い結果を削除して再生成できる設計にしておく |

### 一般テーブル

| テーブル | 保存方針 |
|---|---|
| users | 退職者は `status = 'inactive'` に変更。完全削除は監査ログの SET NULL 後のみ許可 |
| projects | `is_active = FALSE` で論理削除。ドキュメントが残る限り物理削除禁止（RESTRICT FK） |
| approval_workflows / approval_steps | ドキュメント削除に連動（CASCADE） |
