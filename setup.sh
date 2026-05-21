#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo "==> 检查 Python…"
python3 --version

echo "==> 创建虚拟环境…"
python3 -m venv .venv
source .venv/bin/activate

echo "==> 安装 Python 依赖…"
pip install -r requirements.txt

if ! command -v ffmpeg >/dev/null 2>&1; then
  if command -v brew >/dev/null 2>&1; then
    echo "==> 安装 FFmpeg…"
    brew install ffmpeg
  else
    echo "⚠️  未找到 Homebrew，请手动安装 FFmpeg："
    echo "   https://ffmpeg.org/download.html"
    exit 1
  fi
else
  echo "==> FFmpeg 已安装"
  ffmpeg -version | head -1
fi

chmod +x run.sh
echo ""
echo "✅ 安装完成！运行 ./run.sh 启动应用。"
