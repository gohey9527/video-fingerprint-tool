from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def temp_db_path(tmp_path: Path) -> Path:
    return tmp_path / "users.db"


@pytest.fixture
def ffmpeg_available() -> str | None:
    return shutil.which("ffmpeg") or (
        "/opt/homebrew/bin/ffmpeg"
        if Path("/opt/homebrew/bin/ffmpeg").is_file()
        else None
    )


@pytest.fixture
def sample_video(tmp_path: Path, ffmpeg_available: str | None) -> Path:
    if not ffmpeg_available:
        pytest.skip("未安装 FFmpeg")

    output = tmp_path / "sample.mp4"
    command = [
        ffmpeg_available,
        "-y",
        "-f",
        "lavfi",
        "-i",
        "color=c=blue:s=320x240:d=1",
        "-f",
        "lavfi",
        "-i",
        "sine=f=440:d=1",
        "-c:v",
        "libx264",
        "-c:a",
        "aac",
        str(output),
    ]
    subprocess.run(command, check=True, capture_output=True)
    return output
