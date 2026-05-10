---
name: e-submission
description: 電子納品（国交省電子納品要領）対応の実装パターン。PDF/A変換、ファイル命名規則チェック、フォルダ構成検証、しおり自動生成、納品メディア生成などを実装するときに使用。
allowed-tools: Read, Grep, Glob, Bash(npm test *), Bash(pytest *)
---

# E-Submission (電子納品) Patterns

## When to Use
- 電子納品用のPDF/A変換処理の実装時
- ファイル命名規則・フォルダ構成の検証ロジック実装時
- PDFしおり（ブックマーク）の自動生成実装時
- 納品構成チェッカーの実装時
- CORINS/TECRISデータ連携の実装時

## 国交省電子納品要領の基本構成

```
DRAWING/          # 図面
PHOTO/             # 写真
SURVEY/            # 測量
BORING/            # 地質
OTHRS/             # その他
INDEX_D.XML        # 図面管理ファイル
PHOTO.XML          # 写真管理ファイル
```

## PDF/A Requirements

- 最低基準: PDF/A-1b（視覚的再現保証）
- 推奨: PDF/A-2b（JPEG2000圧縮可、透過対応）
- 検証: veraPDF CLI で自動チェック
- フォント: すべて埋め込み必須
- 暗号化: 禁止（PDF/A仕様）

## Validation Rules

- ファイル名: 半角英数字 + アンダースコアのみ
- パス長: 64バイト以内（Shift_JIS換算）
- XML: UTF-8 or Shift_JIS（発注者指定に従う）
- メディア: CD-R / DVD-R（ISO 9660 / UDF）

## Constraints
- 発注者ごとに要領のバージョンが異なる場合がある
- 地方整備局独自のローカルルールが存在する
- 検証ルールはプロファイルとして外部定義ファイル化する
