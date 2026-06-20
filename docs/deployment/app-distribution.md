# 📦 アプリ配信ページ 運用手順（PDF Editor Client）

管理コンソールの「アプリ」ページ（`/apps`）は、デスクトップ **PDF Editor Client**
（建設・土木業向け・電子印鑑/OCR/大判図面対応）を社内・協力会社へ配布する窓口です。

> ⚠️ PDF Editor 本体（デスクトップアプリ）のビルドは本リポジトリ外（Scope B / Issue #62）。
> 本ページはバイナリの**配布窓口**であり、バイナリは CDN / GitHub Releases に配置します。

---

## 📌 1. 提供エンドポイント（要認証）

| メソッド | パス                                  | 用途                                       |
| -------- | ------------------------------------- | ------------------------------------------ |
| GET      | `/api/v1/apps/releases`               | パッケージ一覧 + チャンネル情報            |
| GET      | `/api/v1/apps/release-notes?channel=` | リリースノート（任意でチャンネル絞り込み） |
| GET      | `/api/v1/apps/build-info`             | 配布中ビルドのメタデータ                   |
| GET      | `/api/v1/apps/download/{package_id}`  | ダウンロード URL（未設定時は `url=null`）  |

`package_id`: `win-exe` / `win-zip` / `mac-dmg` / `mac-pkg` / `ent-intune`

---

## 📌 2. 環境変数（`.env.prod`）

| 変数                         | 必須       | 説明                                                                                      |
| ---------------------------- | ---------- | ----------------------------------------------------------------------------------------- |
| `APPS_RELEASE_BASE_URL`      | 配布時必須 | インストーラー配布元のベース URL（CDN / GitHub Releases）。未設定なら「近日公開予定」表示 |
| `APPS_BUILD_NUMBER`          | 任意       | ビルド番号（例 `2.4.1+build.1287`）                                                       |
| `APPS_BUILD_COMMIT`          | 任意       | ビルド元コミット                                                                          |
| `APPS_BUILD_DATE`            | 任意       | ビルド日（ISO 8601）                                                                      |
| `APPS_MIN_SUPPORTED_VERSION` | 任意       | 強制最低バージョン（既定 `2.3.0`）                                                        |
| `APPS_SHA256_<PKG_ID>`       | 任意       | 配布物の SHA-256（例 `APPS_SHA256_WIN_EXE` / `APPS_SHA256_MAC_PKG`）                      |

> 🔢 `APPS_SHA256_<PKG_ID>` の `<PKG_ID>` は package_id をハイフン→アンダースコアにし大文字化（`mac-pkg` → `MAC_PKG`）。

---

## 📌 3. リリース手順

1. PDF Editor 本体をビルドし、各形式を生成（`.exe` / `.zip` / `.dmg` / `.pkg` / `.intunewin`）。
2. チェックサムを生成:
   ```bash
   sha256sum CivilPDF-Editor-Setup-2.4.1.exe
   shasum -a 256 CivilPDF-Editor-2.4.1.pkg
   ```
3. バイナリを `APPS_RELEASE_BASE_URL` 配下（CDN / GitHub Releases）へアップロード。
   - ファイル名は API の `filename`（例 `CivilPDF-Editor-Setup-2.4.1.exe`）と一致させる。
4. `.env.prod` に `APPS_RELEASE_BASE_URL` と各 `APPS_SHA256_*`・`APPS_BUILD_*` を設定。
5. コンソールを再起動し、`/apps` で各パッケージが「準備中」→ サイズ表示に変わることを確認。

---

## 📌 4. macOS 配布形式

| 形式      | 用途                                                    |
| --------- | ------------------------------------------------------- |
| 💿 `.dmg` | 手動インストール（ドラッグ&ドロップ・Universal Binary） |
| 📦 `.pkg` | MDM（Jamf / Intune for macOS）による一括展開            |

> 🍎 **iTunes パッケージ（`.itmsp`）は本配信ページでは扱いません。** App Store 提出専用形式（Transporter 経由）であり、社内配布の窓口に置く対象ではないためです。
> 将来 Mac App Store で配信する場合は `.pkg` + App Store Connect を用い、配信ページではなく App Store 経由となります。

---

## 📌 5. チャンネル運用

| チャンネル | 対象                   | 備考                                 |
| ---------- | ---------------------- | ------------------------------------ |
| Stable     | 全ユーザー（本番推奨） | Beta で 4 週間検証後にリリース       |
| Beta       | 技術担当・検証チーム   | 次期安定版の先行確認                 |
| Insider    | 開発・社内QA           | 破壊的変更を含む可能性。本番利用不可 |

---

## 📌 6. 既知の制約

- 「展開対象」「展開率/バージョン統一率」などの KPI は **MDM 未連携のデモ表示**（UI に「デモ」明示）。
  実数値表示には Intune / Jamf 連携の実装が必要（別 Issue 候補）。
- ダウンロードは `APPS_RELEASE_BASE_URL` 設定後に有効化（未設定時は「近日公開予定」）。
