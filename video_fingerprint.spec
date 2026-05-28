# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置：支持 macOS/Windows。"""

import shutil
import sys
from pathlib import Path

block_cipher = None
project_dir = Path(SPECPATH)
src_dir = project_dir / "src"
app_name = "短视频指纹工具"


def locate_tool(name: str) -> str | None:
    win_name = f"{name}.exe"
    candidates = [
        shutil.which(name),
        shutil.which(win_name),
        f"/opt/homebrew/bin/{name}",
        f"/usr/local/bin/{name}",
        project_dir / "build_resources" / "bin" / name,
        project_dir / "build_resources" / "bin" / win_name,
    ]
    for item in candidates:
        if item and Path(item).is_file():
            return str(Path(item).resolve())
    return None


binaries = []
for tool in ("ffmpeg", "ffprobe"):
    path = locate_tool(tool)
    if path:
        binaries.append((path, "bin"))
    else:
        print(f"[警告] 未找到 {tool}，打包后的应用可能无法处理视频。", file=sys.stderr)

a = Analysis(
    [str(src_dir / "main.py")],
    pathex=[str(src_dir)],
    binaries=binaries,
    datas=[],
    hiddenimports=[
        "processor",
        "fingerprint",
        "bundle_paths",
        "auth",
        "login_window",
        "styles",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=app_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=app_name,
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name=f"{app_name}.app",
        icon=None,
        bundle_identifier="com.videofingerprint.tool",
        info_plist={
            "CFBundleName": app_name,
            "CFBundleDisplayName": "短视频指纹批量修改",
            "CFBundleShortVersionString": "1.0.0",
            "CFBundleVersion": "1.0.0",
            "LSMinimumSystemVersion": "12.0",
            "NSHighResolutionCapable": True,
            "NSRequiresAquaSystemAppearance": False,
        },
    )
