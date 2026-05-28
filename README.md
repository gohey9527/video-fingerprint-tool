# 短视频指纹批量修改工具

桌面工具（支持 macOS / Windows）：拖入一个视频，批量生成多个**指纹不同、内容相同**的视频文件，输出到原视频所在目录。

## 功能

- **账户登录**：需输入账户名和密码后才能使用
- 拖拽或选择单个视频文件
- 自定义生成数量（1–100）
- 一键批量生成，保存到原视频目录
- 每个输出视频采用不同的微参数组合（速度、亮度、对比度、裁剪、元数据、编码参数等），改变文件指纹

## 环境要求

- macOS 或 Windows
- Python 3.10+
- FFmpeg（macOS: `brew install ffmpeg`，Windows: 安装后加入 PATH）

## 快速开始

```bash
# 1. 安装依赖
./setup.sh

# 2. 启动应用
./run.sh
```

## 账户登录

首次启动会自动创建默认管理员：

| 项目 | 值 |
|------|-----|
| 账户名 | `admin` |
| 密码 | `admin123` |

登录后请尽快修改默认密码。

### 管理用户账户

```bash
cd /Users/shudong/video-fingerprint-tool
source .venv/bin/activate

# 添加用户
python scripts/manage_users.py add 用户名 密码

# 修改密码
python scripts/manage_users.py passwd admin 新密码

# 列出用户
python scripts/manage_users.py list

# 禁用用户
python scripts/manage_users.py disable 用户名
```

用户数据保存在：`~/Library/Application Support/短视频指纹工具/users.db`

## 使用说明

1. 打开应用，使用账户名和密码登录
2. 将视频拖入虚线区域，或点击「选择视频文件」
2. 设置「生成数量」
3. 点击「生成视频」
4. 完成后，在原视频目录下会生成类似 `原文件名_指纹_001.mp4` 的文件

## 指纹修改策略

每个输出视频会随机组合以下不可感知微调：

| 类型 | 说明 |
|------|------|
| 播放速度 | ±0.4% 微调 |
| 画面 | 轻微缩放、裁剪、旋转 |
| 色彩 | 亮度 / 对比度 / 饱和度 / 色相微调 |
| 音频 | 速度与音量同步微调 |
| 编码 | 不同 CRF 值重新编码 |
| 元数据 | 随机 title / comment / encoder |
| 噪点 | 极低强度噪点 |

## 项目结构

```
video-fingerprint-tool/
├── setup.sh          # 一键安装
├── run.sh            # 启动应用
├── requirements.txt
└── src/
    ├── main.py           # PyQt6 界面
    ├── processor.py      # FFmpeg 处理
    └── fingerprint.py    # 指纹参数生成
```

## 打包成 Mac 应用（.app）

在 **macOS** 上运行以下命令，会生成可双击运行的应用包：

```bash
# 先确保已安装 FFmpeg
brew install ffmpeg

# 一键打包
chmod +x build_app.sh
./build_app.sh
```

打包完成后，应用位于：

```
dist/短视频指纹工具.app
```

### 使用打包好的应用

1. 双击 `dist/短视频指纹工具.app` 运行
2. 或把 `.app` 拖到「应用程序」文件夹，从启动台打开
3. 若系统提示「无法验证开发者」：**右键 → 打开**（首次即可）

### 从 GitHub Releases 下载 Mac 版

1. 打开 [Releases 页面](https://github.com/gohey9527/video-fingerprint-tool/releases)
2. 选择 **macOS 最新版**（`macos-latest`）
3. 下载 `短视频指纹工具-macOS-arm64.zip`（适用于 M 系列 Mac）

### 打包说明

| 项目 | 说明 |
|------|------|
| 工具 | PyInstaller |
| 内置 FFmpeg | 打包时自动复制进应用，用户无需再装 |
| 体积 | 约 150–250 MB（含 FFmpeg + PyQt6） |
| 分发 | 可直接拷贝 `.app` 给其他 Mac 用户使用 |

### 常见问题

**Q: 提示「已损坏，无法打开」？**

```bash
xattr -cr "dist/短视频指纹工具.app"
```

**Q: 想给别人用，需要签名吗？**

本地或熟人使用：右键打开即可。若要公开发布，需 Apple 开发者账号做代码签名与公证（Notarization）。

## 打包成 Windows 应用（.exe）

请在 **Windows** 机器上运行（不能在 macOS 交叉打包）：

```bat
build_windows.bat
```

完成后输出：

```
release/短视频指纹工具.exe
release/短视频指纹工具-windows.zip
```

### Windows 说明

| 项目 | 说明 |
|------|------|
| 工具 | PyInstaller |
| 内置 FFmpeg | 打包时自动复制 `ffmpeg.exe` / `ffprobe.exe` |
| 首次运行拦截 | 若出现 SmartScreen，点“更多信息”→“仍要运行” |
| 分发方式 | 推荐发送 `release/短视频指纹工具-windows.zip` |

### 在 Mac 上自动打 Windows 包（GitHub Actions）

Mac 无法本地交叉编译 Windows 可执行文件，但可以把代码推到 GitHub，由 CI 在 Windows 环境自动打包。

**下载方式（推荐）：**

1. 打开仓库右侧 **Releases**（或访问 [Releases 页面](https://github.com/gohey9527/video-fingerprint-tool/releases)）
2. 下载对应平台版本：
   - **macOS 最新版** → `短视频指纹工具-macOS-arm64.zip`
   - **Windows 最新版** → `短视频指纹工具-windows.zip`

**备用方式（Actions Artifacts）：**

1. 打开 **Actions → Build Windows Release**
2. 进入最新一次成功运行
3. 在 **Artifacts** 下载 `video-fingerprint-tool-windows`

## 注意事项

- 视频越长，生成耗时越多（每个文件需重新编码）
- 建议先用 1–2 个测试，确认效果后再批量生成
- 本工具仅改变文件指纹，不改变肉眼可见的内容
