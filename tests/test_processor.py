from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from fingerprint import generate_fingerprints
from processor import (
    build_ffmpeg_command,
    build_output_path,
    build_resolution_guard_filter,
    detect_aspect_category,
    find_ffmpeg,
    format_file_size,
    is_video_file,
    parse_ffmpeg_progress,
    probe_video_dimensions,
    process_videos,
    resolve_min_resolution,
)


def test_is_video_file_accepts_common_extensions() -> None:
    assert is_video_file(Path("clip.mp4"))
    assert is_video_file(Path("clip.MOV"))
    assert not is_video_file(Path("notes.txt"))


def test_build_output_path_uses_fingerprint_suffix() -> None:
    source = Path("/tmp/demo/source.mp4")
    assert build_output_path(source, 2) == Path("/tmp/demo/source_指纹_002.mp4")


def test_parse_ffmpeg_progress_returns_ratio() -> None:
    assert parse_ffmpeg_progress("out_time_ms=500000", 1_000_000) == 0.5
    assert parse_ffmpeg_progress("out_time_ms=2000000", 1_000_000) == 1.0
    assert parse_ffmpeg_progress("progress=continue", 1_000_000) is None


def test_format_file_size() -> None:
    assert format_file_size(512) == "512.0 B"
    assert format_file_size(2048) == "2.0 KB"


def test_build_ffmpeg_command_includes_metadata_and_filters() -> None:
    params = generate_fingerprints("/tmp/demo.mp4", 1)[0]
    command = build_ffmpeg_command(
        "/opt/homebrew/bin/ffmpeg",
        Path("/tmp/demo.mp4"),
        Path("/tmp/demo_指纹_001.mp4"),
        params,
        source_width=720,
        source_height=1280,
    )
    joined = " ".join(command)
    assert "-vf" in command
    assert "-af" in command
    assert params.metadata_title in joined
    assert "force_original_aspect_ratio=increase" in joined
    assert str(Path("/tmp/demo_指纹_001.mp4")) in command


def test_detect_aspect_category_for_vertical_9_16() -> None:
    assert detect_aspect_category(720, 1280) == "9:16"
    assert detect_aspect_category(1080, 1920) == "9:16"


def test_resolve_min_resolution_for_9_16() -> None:
    assert resolve_min_resolution(720, 1280) == (720, 1280)


def test_build_resolution_guard_filter() -> None:
    assert "720:1280" in build_resolution_guard_filter(720, 1280)


def test_process_videos_rejects_missing_file() -> None:
    if find_ffmpeg() is None:
        pytest.skip("未安装 FFmpeg")
    with pytest.raises(FileNotFoundError):
        process_videos("/tmp/does-not-exist-video.mp4", 1)


@pytest.mark.integration
def test_process_videos_generates_outputs(sample_video: Path, tmp_path: Path) -> None:
    working_copy = tmp_path / sample_video.name
    working_copy.write_bytes(sample_video.read_bytes())

    outputs = process_videos(str(working_copy), 2)
    assert len(outputs) == 2
    for path in outputs:
        output = Path(path)
        assert output.is_file()
        assert output.stat().st_size > 0
        assert output.name.endswith(".mp4")


@pytest.mark.integration
def test_process_videos_preserves_9_16_minimum_resolution(
    tmp_path: Path,
    ffmpeg_available: str | None,
) -> None:
    if not ffmpeg_available:
        pytest.skip("未安装 FFmpeg")

    source = tmp_path / "vertical.mp4"
    command = [
        ffmpeg_available,
        "-y",
        "-f",
        "lavfi",
        "-i",
        "color=c=blue:s=720x1280:d=1",
        "-f",
        "lavfi",
        "-i",
        "sine=f=440:d=1",
        "-c:v",
        "libx264",
        "-c:a",
        "aac",
        str(source),
    ]
    subprocess.run(command, check=True, capture_output=True)

    outputs = process_videos(str(source), 3)
    assert len(outputs) == 3
    for path in outputs:
        dimensions = probe_video_dimensions(Path(path))
        assert dimensions is not None
        width, height = dimensions
        assert width >= 720, f"宽度过小: {width}"
        assert height >= 1280, f"高度过小: {height}"
