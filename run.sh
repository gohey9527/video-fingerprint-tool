#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

if ! command -v python3 >/dev/null 2>&1; then
  echo "未找到 python3，请先安装 Python 3。"
  exit 1
fi

if [ ! -d ".venv" ]; then
  echo "正在创建虚拟环境…"
  python3 -m venv .venv
fi

source .venv/bin/activate
pip install -q -r requirements.txt

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo ""
  echo "⚠️  未检测到 FFmpeg。视频处理需要 FFmpeg。"
  echo "   请运行：brew install ffmpeg"
  echo ""
fi

cd src
python3 main.py
