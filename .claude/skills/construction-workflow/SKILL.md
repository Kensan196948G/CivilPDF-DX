---
name: construction-workflow
description: 建設業の承認ワークフロー実装パターン。承認・差戻し・回覧フロー、電子印鑑、現場別権限管理などの建設業務ロジックを書くときに使用。
allowed-tools: Read, Grep, Glob, Bash(pytest *)
---

# Construction Workflow Patterns

## When to Use
- 承認ワークフロー（申請→確認→承認→差戻し）の実装時
- 電子印鑑（承認印・確認印・日付印）の実装時
- 現場別・工事案件別の権限管理の実装時
- 協力会社の期限付きアクセス管理の実装時

## Domain Model

### 承認ステータス
```
draft → submitted → reviewing → approved → archived
                  ↘ rejected → resubmitted → reviewing
```

### 組織階層と権限
```
本社（headquarters）    — 全現場閲覧・最終承認権限
支店（branch）         — 管轄現場の閲覧・承認権限
現場事務所（field）     — 当該現場の編集・申請権限
モバイル（mobile）     — 閲覧・写真撮影・簡易注釈権限
協力会社（partner）    — 指定文書の閲覧・提出権限（期限付き）
```

## API Design

- `POST /api/v1/workflows/` — ワークフロー作成
- `POST /api/v1/workflows/{id}/submit` — 申請
- `POST /api/v1/workflows/{id}/approve` — 承認
- `POST /api/v1/workflows/{id}/reject` — 差戻し（理由必須）
- `GET /api/v1/workflows/?site_id={id}&status={status}` — 現場別一覧

## Constraints
- 承認履歴は追記専用（DELETE/UPDATE不可）
- 差戻し時は理由コメント必須
- 代理承認は事前の委任設定が必要
- 監査ログは全操作を記録
