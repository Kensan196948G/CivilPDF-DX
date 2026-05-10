---
name: pdf-processing
description: PDF操作の実装パターン。PDF結合、分割、注釈追加、PDF/A変換、電子署名、メタデータ編集などのPDF処理コードを書くときに使用。
allowed-tools: Read, Grep, Glob, Bash(npm test *)
---

# PDF Processing Patterns

## When to Use
- PDF結合・分割・ページ操作の実装時
- PDF注釈（テキスト・図形・ハイライト）の追加時
- PDF/A変換処理の実装時
- 電子署名・タイムスタンプの実装時
- PDFメタデータ（しおり・プロパティ）の操作時

## Libraries

- `pdf-lib` — PDF生成・編集（MIT License）
- `qpdf` — PDF変換・最適化（Apache 2.0）
- `veraPDF` — PDF/A検証（GPL dual / MPL 2.0 — CLIとして外部実行のみ）
- `Poppler utils` — pdftotext, pdfimages 等のCLIツール

## Core Patterns

### PDF結合
```typescript
import { PDFDocument } from 'pdf-lib';

async function mergePdfs(pdfBuffers: Uint8Array[]): Promise<Uint8Array> {
  const merged = await PDFDocument.create();
  for (const buffer of pdfBuffers) {
    const doc = await PDFDocument.load(buffer);
    const pages = await merged.copyPages(doc, doc.getPageIndices());
    pages.forEach(page => merged.addPage(page));
  }
  return merged.save();
}
```

### PDF/A変換
- qpdf CLIを外部プロセスとして実行
- veraPDF CLIで検証（プロセス内リンクしない→GPL汚染回避）

## Constraints
- GPL系ライブラリはプロセス内リンク禁止（CLI外部実行のみ）
- 大判PDF（A0/A1）は遅延レンダリング必須
- メモリ上限を意識（100MB超のPDFはストリーミング処理）
