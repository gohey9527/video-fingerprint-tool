#!/bin/bash
# 打包为可分发的 macOS .app（内置 FFmpeg，其它 Mac 解压即用）
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

APP_NAME="短视频指纹工具"
DIST_APP="dist/${APP_NAME}.app"
RELEASE_DIR="release"
ARCH="$(uname -m)"
ZIP_NAME="${APP_NAME}-macOS-${ARCH}.zip"

echo "==> 检查运行环境（需要 macOS）"
if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "错误：只能在 macOS 上打包 .app"
  exit 1
fi

echo "==> 检查 FFmpeg（会内置进应用，使用者无需安装）"
FFMPEG=""
FFPROBE=""
for dir in /opt/homebrew/bin /usr/local/bin /opt/local/bin; do
  if [[ -x "${dir}/ffmpeg" ]]; then FFMPEG="${dir}/ffmpeg"; fi
  if [[ -x "${dir}/ffprobe" ]]; then FFPROBE="${dir}/ffprobe"; fi
done
if [[ -z "$FFMPEG" ]]; then FFMPEG="$(command -v ffmpeg || true)"; fi
if [[ -z "$FFPROBE" ]]; then FFPROBE="$(command -v ffprobe || true)"; fi

if [[ -z "$FFMPEG" || -z "$FFPROBE" ]]; then
  echo ""
  echo "未找到 FFmpeg，请先安装："
  echo "  brew install ffmpeg"
  echo ""
  exit 1
fi

echo "    ffmpeg:  $FFMPEG"
echo "    ffprobe: $FFPROBE"
echo "    目标架构: $ARCH"

mkdir -p build_resources/bin
cp -f "$FFMPEG" build_resources/bin/ffmpeg
cp -f "$FFPROBE" build_resources/bin/ffprobe
chmod +x build_resources/bin/ffmpeg build_resources/bin/ffprobe

echo "==> 准备 Python 虚拟环境"
if [[ ! -d ".venv" ]]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

echo "==> 安装依赖"
pip install -q --upgrade pip
pip install -q -r requirements.txt -r requirements-build.txt

echo "==> 清理旧构建"
rm -rf build dist "$RELEASE_DIR"

echo "==> 开始打包（约 1–3 分钟）"
pyinstaller video_fingerprint.spec --noconfirm

if [[ ! -d "$DIST_APP" ]]; then
  echo "错误：未找到输出应用 $DIST_APP"
  exit 1
fi

echo "==> 签名应用（便于其它 Mac 打开）"
# 先签名内置的 ffmpeg/ffprobe，再签名整个包
find "$DIST_APP" -type f \( -name ffmpeg -o -name ffprobe \) -print0 2>/dev/null | while IFS= read -r -d '' bin; do
  codesign --force --sign - --entitlements entitlements.plist "$bin" 2>/dev/null || codesign --force --sign - "$bin"
done
codesign --force --deep --sign - --entitlements entitlements.plist "$DIST_APP" 2>/dev/null \
  || codesign --force --deep --sign - "$DIST_APP"

xattr -cr "$DIST_APP" 2>/dev/null || true

echo "==> 生成分发压缩包"
mkdir -p "$RELEASE_DIR"

cat > "$RELEASE_DIR/使用说明.txt" <<EOF
短视频指纹批量修改工具 - 使用说明
================================

【系统要求】
- macOS 12.0 或更高
- 本安装包架构：${ARCH}
  $(if [[ "$ARCH" == "arm64" ]]; then echo "  - 适用于 Apple 芯片 Mac（M1/M2/M3/M4）"; else echo "  - 适用于 Intel 芯片 Mac"; fi)

【安装】
1. 解压 zip 文件
2. 将「${APP_NAME}.app」拖到「应用程序」文件夹（或任意位置）

【首次打开】
若提示「无法打开」或「来自未知开发者」：
  方法一：右键点击应用 → 选择「打开」→ 再点「打开」
  方法二：打开终端执行：
    xattr -cr "/路径/${APP_NAME}.app"

【使用】
1. 打开应用
2. 拖入视频文件
3. 设置生成数量
4. 点击「生成视频」
5. 新视频会保存在原视频同一文件夹

【说明】
- 应用已内置 FFmpeg，无需额外安装
- 可直接拷贝 .app 给其它 Mac 使用（需相同芯片类型：${ARCH}）
EOF

(
  cd dist
  ditto -c -k --sequesterRsrc --keepParent "${APP_NAME}.app" "../${RELEASE_DIR}/${ZIP_NAME}"
)

cp -R "$DIST_APP" "$RELEASE_DIR/${APP_NAME}.app"

APP_SIZE="$(du -sh "$RELEASE_DIR/${ZIP_NAME}" | cut -f1)"

echo ""
echo "============================================"
echo "  ✅ 打包完成！可发给其它 Mac 使用"
echo "============================================"
echo ""
echo "  应用本体："
echo "    $ROOT/$RELEASE_DIR/${APP_NAME}.app"
echo ""
echo "  分发压缩包（推荐发这个）："
echo "    $ROOT/$RELEASE_DIR/${ZIP_NAME}"
echo "    大小约：${APP_SIZE}"
echo ""
echo "  芯片说明："
if [[ "$ARCH" == "arm64" ]]; then
  echo "    当前为 Apple 芯片版 (arm64)，适用于 M 系列 Mac"
  echo "    Intel Mac 需要在 Intel 电脑上重新运行 ./build_app.sh 打包"
else
  echo "    当前为 Intel 芯片版 (x86_64)"
fi
echo ""
echo "  发给他人：把 ${ZIP_NAME} 通过微信/网盘/U盘发送即可"
echo ""

open "$RELEASE_DIR"
