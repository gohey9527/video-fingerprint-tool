"""在 .app 包内定位内置资源（如 FFmpeg）。"""

from __future__ import annotations

import sys
from pathlib import Path


def bundle_root() -> Path | None:
    """返回打包应用内的资源根目录，开发模式下返回 None。"""
    if not getattr(sys, "frozen", False):
        return None

    # PyInstaller 单目录 / .app
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass)

    # py2app: Contents/MacOS/executable -> Contents/Resources
    exe = Path(sys.executable)
    resources = exe.parent.parent / "Resources"
    if resources.is_dir():
        return resources

    return exe.parent


def bundled_binary(name: str) -> Path | None:
    root = bundle_root()
    if not root:
        return None
    candidates = [root / "bin" / name]
    if sys.platform.startswith("win"):
        candidates.append(root / "bin" / f"{name}.exe")
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None
