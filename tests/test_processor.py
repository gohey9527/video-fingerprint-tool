from __future__ import annotations

from pathlib import Path

import pytest

from fingerprint import generate_fingerprints
from processor import (
    build_ffmpeg_command,
    build_output_path,
    find_ffmpeg,
    format_file_size,
    is_video_file,
    parse_ffmpeg_progress,
    process_videos,
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
    )
    joined = " ".join(command)
    assert "-vf" in command
    assert "-af" in command
    assert params.metadata_title in joined
    assert str(Path("/tmp/demo_指纹_001.mp4")) in command


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
