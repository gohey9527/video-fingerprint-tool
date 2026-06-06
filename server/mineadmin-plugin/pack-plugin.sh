#!/usr/bin/env bash
# 将 client-usage 插件打包为 zip，便于 MineAdmin 后台「本地上传安装」
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_DIR="$ROOT/client-usage"
OUTPUT="$ROOT/client-usage.zip"

if [[ ! -f "$PLUGIN_DIR/mine.json" ]]; then
  echo "错误：未找到 $PLUGIN_DIR/mine.json"
  exit 1
fi

rm -f "$OUTPUT"
cd "$ROOT"
zip -r "$OUTPUT" client-usage \
  -x "*/.DS_Store" \
  -x "*/__MACOSX/*"

echo "已生成：$OUTPUT"
echo "请在 MineAdmin 后台 → 插件管理 → 本地上传安装"
