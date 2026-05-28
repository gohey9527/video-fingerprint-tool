@echo off
setlocal enabledelayedexpansion

REM 打包为可分发的 Windows 版本（内置 ffmpeg/ffprobe）

set "ROOT=%~dp0"
cd /d "%ROOT%"

set "APP_NAME=短视频指纹工具"
set "RELEASE_DIR=release"
set "DIST_DIR=dist\%APP_NAME%"
set "ZIP_NAME=%APP_NAME%-windows.zip"

echo ==> 检查运行环境（需要 Windows）
if /I not "%OS%"=="Windows_NT" (
  echo 错误：只能在 Windows 上运行此脚本
  exit /b 1
)

echo ==> 检查 FFmpeg（会内置进应用，使用者无需安装）
powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%scripts\prepare_ffmpeg_windows.ps1"
if errorlevel 1 (
  echo 错误：准备 FFmpeg 失败
  exit /b 1
)

set "FFMPEG=%ROOT%build_resources\bin\ffmpeg.exe"
set "FFPROBE=%ROOT%build_resources\bin\ffprobe.exe"
if not exist "%FFMPEG%" (
  echo 错误：未找到 build_resources\bin\ffmpeg.exe
  exit /b 1
)
if not exist "%FFPROBE%" (
  echo 错误：未找到 build_resources\bin\ffprobe.exe
  exit /b 1
)

echo     ffmpeg:  %FFMPEG%
echo     ffprobe: %FFPROBE%

echo ==> 准备 Python 虚拟环境
if not exist ".venv\Scripts\python.exe" (
  py -3 -m venv .venv || python -m venv .venv
)
if not exist ".venv\Scripts\python.exe" (
  echo 错误：虚拟环境创建失败，请检查 Python 安装
  exit /b 1
)

call ".venv\Scripts\activate.bat"
if errorlevel 1 (
  echo 错误：无法激活虚拟环境
  exit /b 1
)

echo ==> 安装依赖
python -m pip install -q --upgrade pip
python -m pip install -q -r requirements.txt -r requirements-build.txt

echo ==> 清理旧构建
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist "%RELEASE_DIR%" rmdir /s /q "%RELEASE_DIR%"

echo ==> 开始打包（约 1–3 分钟）
pyinstaller video_fingerprint.spec --noconfirm
if errorlevel 1 (
  echo 错误：PyInstaller 打包失败
  exit /b 1
)

if not exist "%DIST_DIR%" (
  echo 错误：未找到输出目录 %DIST_DIR%
  exit /b 1
)

echo ==> 验证内置 FFmpeg
set "PACKAGED_FFMPEG=%DIST_DIR%\_internal\bin\ffmpeg.exe"
set "PACKAGED_FFPROBE=%DIST_DIR%\_internal\bin\ffprobe.exe"
if not exist "%PACKAGED_FFMPEG%" (
  echo 错误：打包结果中未找到 %PACKAGED_FFMPEG%
  exit /b 1
)
if not exist "%PACKAGED_FFPROBE%" (
  echo 错误：打包结果中未找到 %PACKAGED_FFPROBE%
  exit /b 1
)
"%PACKAGED_FFMPEG%" -version >nul 2>&1
if errorlevel 1 (
  echo 错误：内置 ffmpeg.exe 无法运行（可能是 Chocolatey 快捷方式）
  exit /b 1
)
"%PACKAGED_FFPROBE%" -version >nul 2>&1
if errorlevel 1 (
  echo 错误：内置 ffprobe.exe 无法运行
  exit /b 1
)
echo     packaged ffmpeg:  %PACKAGED_FFMPEG%
echo     packaged ffprobe: %PACKAGED_FFPROBE%

echo ==> 生成分发包
mkdir "%RELEASE_DIR%"
copy /Y "dist\%APP_NAME%.exe" "%RELEASE_DIR%\%APP_NAME%.exe" >nul

powershell -NoProfile -Command ^
  "Compress-Archive -Path '%ROOT%dist\%APP_NAME%\*' -DestinationPath '%ROOT%%RELEASE_DIR%\%ZIP_NAME%' -Force"
if errorlevel 1 (
  echo 错误：压缩包生成失败
  exit /b 1
)

(
  echo 短视频指纹批量修改工具 - Windows 使用说明
  echo ========================================
  echo.
  echo 【系统要求】
  echo - Windows 10/11 x64
  echo.
  echo 【使用方法】
  echo 1. 解压 %ZIP_NAME%
  echo 2. 双击目录中的「%APP_NAME%.exe」
  echo 3. 首次运行若被 SmartScreen 拦截，点击“更多信息”后选择“仍要运行”
  echo.
  echo 【说明】
  echo - 已内置 ffmpeg/ffprobe，用户无需额外安装
  echo - 输出视频仍保存在原视频目录
) > "%RELEASE_DIR%\使用说明-Windows.txt"

echo.
echo ============================================
echo   ✅ Windows 打包完成
echo ============================================
echo.
echo   单文件入口：
echo     %ROOT%%RELEASE_DIR%\%APP_NAME%.exe
echo.
echo   分发压缩包：
echo     %ROOT%%RELEASE_DIR%\%ZIP_NAME%
echo.

endlocal
