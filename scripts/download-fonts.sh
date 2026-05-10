#!/usr/bin/env bash
# =============================================================================
# CivilPDF-DX フォントダウンロードスクリプト
# 16書体（3層構成）を Google Fonts / GitHub から取得する
# =============================================================================

set -euo pipefail

FONT_DIR="$(cd "$(dirname "$0")/../assets/fonts" && pwd)"
TEMP_DIR="$(mktemp -d)"

echo "================================================"
echo "CivilPDF-DX フォントダウンロード"
echo "保存先: ${FONT_DIR}"
echo "================================================"

# --- 第1層: 必須フォント (Noto系) ---
echo ""
echo "[第1層] 必須フォント (Noto Sans/Serif/Mono JP)"
echo "------------------------------------------------"

# Noto Sans JP
echo "  Downloading Noto Sans JP..."
curl -sL "https://fonts.google.com/download?family=Noto+Sans+JP" -o "${TEMP_DIR}/NotoSansJP.zip"
unzip -qo "${TEMP_DIR}/NotoSansJP.zip" -d "${TEMP_DIR}/NotoSansJP"
cp "${TEMP_DIR}/NotoSansJP/static/NotoSansJP-Regular.ttf" "${FONT_DIR}/tier1-core/" 2>/dev/null || \
cp "${TEMP_DIR}/NotoSansJP/"*Regular*.ttf "${FONT_DIR}/tier1-core/NotoSansJP-Regular.ttf" 2>/dev/null || true
cp "${TEMP_DIR}/NotoSansJP/static/NotoSansJP-Bold.ttf" "${FONT_DIR}/tier1-core/" 2>/dev/null || \
cp "${TEMP_DIR}/NotoSansJP/"*Bold*.ttf "${FONT_DIR}/tier1-core/NotoSansJP-Bold.ttf" 2>/dev/null || true
echo "  ✓ Noto Sans JP (Regular, Bold)"

# Noto Serif JP
echo "  Downloading Noto Serif JP..."
curl -sL "https://fonts.google.com/download?family=Noto+Serif+JP" -o "${TEMP_DIR}/NotoSerifJP.zip"
unzip -qo "${TEMP_DIR}/NotoSerifJP.zip" -d "${TEMP_DIR}/NotoSerifJP"
cp "${TEMP_DIR}/NotoSerifJP/static/NotoSerifJP-Regular.ttf" "${FONT_DIR}/tier1-core/" 2>/dev/null || \
cp "${TEMP_DIR}/NotoSerifJP/"*Regular*.ttf "${FONT_DIR}/tier1-core/NotoSerifJP-Regular.ttf" 2>/dev/null || true
cp "${TEMP_DIR}/NotoSerifJP/static/NotoSerifJP-Bold.ttf" "${FONT_DIR}/tier1-core/" 2>/dev/null || \
cp "${TEMP_DIR}/NotoSerifJP/"*Bold*.ttf "${FONT_DIR}/tier1-core/NotoSerifJP-Bold.ttf" 2>/dev/null || true
echo "  ✓ Noto Serif JP (Regular, Bold)"

# Noto Sans Mono CJK JP
echo "  Downloading Noto Sans Mono CJK JP..."
curl -sL "https://github.com/notofonts/noto-cjk/releases/latest/download/08_NotoSansMonoCJKjp.zip" -o "${TEMP_DIR}/NotoSansMono.zip" 2>/dev/null || \
curl -sL "https://github.com/googlefonts/noto-cjk/releases/latest/download/08_NotoSansMonoCJKjp.zip" -o "${TEMP_DIR}/NotoSansMono.zip" 2>/dev/null || true
if [ -f "${TEMP_DIR}/NotoSansMono.zip" ]; then
  unzip -qo "${TEMP_DIR}/NotoSansMono.zip" -d "${TEMP_DIR}/NotoSansMono"
  find "${TEMP_DIR}/NotoSansMono" -name "*Regular*" -exec cp {} "${FONT_DIR}/tier1-core/NotoSansMonoCJKjp-Regular.ttf" \; 2>/dev/null || true
  find "${TEMP_DIR}/NotoSansMono" -name "*Bold*" ! -name "*Semi*" ! -name "*Extra*" -exec cp {} "${FONT_DIR}/tier1-core/NotoSansMonoCJKjp-Bold.ttf" \; 2>/dev/null || true
  echo "  ✓ Noto Sans Mono CJK JP (Regular, Bold)"
else
  echo "  ⚠ Noto Sans Mono CJK JP - 手動ダウンロードが必要です"
  echo "    https://github.com/notofonts/noto-cjk/releases"
fi

# --- 第2層: 互換性フォント ---
echo ""
echo "[第2層] 互換性フォント (IPAex, Liberation)"
echo "------------------------------------------------"

# IPAex Fonts
echo "  Downloading IPAex Fonts..."
curl -sL "https://moji.or.jp/wp-content/ipafont/IPAexfont/IPAexfont00401.zip" -o "${TEMP_DIR}/IPAex.zip" 2>/dev/null || true
if [ -f "${TEMP_DIR}/IPAex.zip" ]; then
  unzip -qo "${TEMP_DIR}/IPAex.zip" -d "${TEMP_DIR}/IPAex"
  find "${TEMP_DIR}/IPAex" -name "ipaexg.ttf" -exec cp {} "${FONT_DIR}/tier2-compat/" \; 2>/dev/null || true
  find "${TEMP_DIR}/IPAex" -name "ipaexm.ttf" -exec cp {} "${FONT_DIR}/tier2-compat/" \; 2>/dev/null || true
  echo "  ✓ IPAex Gothic, IPAex Mincho"
else
  echo "  ⚠ IPAex Fonts - 手動ダウンロードが必要です"
  echo "    https://moji.or.jp/ipafont/ipafontdownload/"
fi

# Liberation Fonts
echo "  Downloading Liberation Fonts..."
curl -sL "https://github.com/liberationfonts/liberation-fonts/files/7261482/liberation-fonts-ttf-2.1.5.tar.gz" -o "${TEMP_DIR}/liberation.tar.gz" 2>/dev/null || true
if [ -f "${TEMP_DIR}/liberation.tar.gz" ]; then
  tar xzf "${TEMP_DIR}/liberation.tar.gz" -C "${TEMP_DIR}/"
  LIBDIR=$(find "${TEMP_DIR}" -type d -name "liberation-fonts-ttf-*" | head -1)
  if [ -n "$LIBDIR" ]; then
    cp "${LIBDIR}/LiberationSans-Regular.ttf" "${FONT_DIR}/tier2-compat/" 2>/dev/null || true
    cp "${LIBDIR}/LiberationSans-Bold.ttf" "${FONT_DIR}/tier2-compat/" 2>/dev/null || true
    cp "${LIBDIR}/LiberationSerif-Regular.ttf" "${FONT_DIR}/tier2-compat/" 2>/dev/null || true
    cp "${LIBDIR}/LiberationSerif-Bold.ttf" "${FONT_DIR}/tier2-compat/" 2>/dev/null || true
    cp "${LIBDIR}/LiberationMono-Regular.ttf" "${FONT_DIR}/tier3-specialized/" 2>/dev/null || true
    echo "  ✓ Liberation Sans, Serif (Regular, Bold), Mono (Regular)"
  fi
else
  echo "  ⚠ Liberation Fonts - 手動ダウンロードが必要です"
  echo "    https://github.com/liberationfonts/liberation-fonts/releases"
fi

# --- 第3層: 業務特化フォント ---
echo ""
echo "[第3層] 業務特化フォント (BIZ UD)"
echo "------------------------------------------------"

# BIZ UDGothic
echo "  Downloading BIZ UDGothic..."
curl -sL "https://fonts.google.com/download?family=BIZ+UDGothic" -o "${TEMP_DIR}/BIZUDGothic.zip" 2>/dev/null || true
if [ -f "${TEMP_DIR}/BIZUDGothic.zip" ]; then
  unzip -qo "${TEMP_DIR}/BIZUDGothic.zip" -d "${TEMP_DIR}/BIZUDGothic"
  find "${TEMP_DIR}/BIZUDGothic" -name "*Regular*" -exec cp {} "${FONT_DIR}/tier3-specialized/BIZUDGothic-Regular.ttf" \; 2>/dev/null || true
  find "${TEMP_DIR}/BIZUDGothic" -name "*Bold*" -exec cp {} "${FONT_DIR}/tier3-specialized/BIZUDGothic-Bold.ttf" \; 2>/dev/null || true
  echo "  ✓ BIZ UDGothic (Regular, Bold)"
fi

# BIZ UDMincho
echo "  Downloading BIZ UDMincho..."
curl -sL "https://fonts.google.com/download?family=BIZ+UDMincho" -o "${TEMP_DIR}/BIZUDMincho.zip" 2>/dev/null || true
if [ -f "${TEMP_DIR}/BIZUDMincho.zip" ]; then
  unzip -qo "${TEMP_DIR}/BIZUDMincho.zip" -d "${TEMP_DIR}/BIZUDMincho"
  find "${TEMP_DIR}/BIZUDMincho" -name "*Regular*" -exec cp {} "${FONT_DIR}/tier3-specialized/BIZUDMincho-Regular.ttf" \; 2>/dev/null || true
  echo "  ✓ BIZ UDMincho (Regular)"
fi

# --- ライセンスファイル ---
echo ""
echo "[ライセンス] ライセンスファイルの配置"
echo "------------------------------------------------"

# SIL OFL 1.1
cat > "${FONT_DIR}/LICENSES/SIL-OFL-1.1.txt" << 'EOF'
Copyright (c) Google LLC, Adobe Inc., and contributors.

This Font Software is licensed under the SIL Open Font License, Version 1.1.
This license is available with a FAQ at: https://openfontlicense.org

SIL OPEN FONT LICENSE Version 1.1 - 26 February 2007
https://openfontlicense.org/open-font-license-official-text/
EOF
echo "  ✓ SIL-OFL-1.1.txt"

# IPA Font License
cat > "${FONT_DIR}/LICENSES/IPA-Font-License.txt" << 'EOF'
IPA Font License Agreement v1.0

https://moji.or.jp/ipafont/license/

The Licensor provides the Licensed Program (as defined in Article 1 below)
under the terms of this license agreement ("Agreement").
Any use, reproduction or distribution of the Licensed Program, or any
exercise of rights under this Agreement by a Recipient (as defined in
Article 1 below) constitutes the Recipient's acceptance of this Agreement.
EOF
echo "  ✓ IPA-Font-License.txt"

# --- クリーンアップ ---
rm -rf "${TEMP_DIR}"

# --- 結果確認 ---
echo ""
echo "================================================"
echo "ダウンロード完了"
echo "================================================"
echo ""
echo "配置されたフォント:"
find "${FONT_DIR}" -name "*.ttf" -o -name "*.otf" | sort | while read f; do
  SIZE=$(du -h "$f" | cut -f1)
  echo "  ${SIZE}  $(basename "$f")"
done
TOTAL=$(du -sh "${FONT_DIR}" | cut -f1)
echo ""
echo "合計: ${TOTAL}"
echo ""
echo "注意: ダウンロードに失敗したフォントがある場合は、上記の URL から手動でダウンロードしてください。"
