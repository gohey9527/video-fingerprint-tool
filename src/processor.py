"""使用 FFmpeg 批量生成不同指纹的视频。"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Callable

from bundle_paths import bundled_binary
from fingerprint import FingerprintParams, generate_fingerprints

VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".m4v", ".webm", ".flv", ".wmv"}


def find_ffmpeg() -> str | None:
    bundled = bundled_binary("ffmpeg")
    if bundled:
        return str(bundled)
    path = shutil.which("ffmpeg")
    if path:
        return path
    for candidate in (
        "/opt/homebrew/bin/ffmpeg",
        "/usr/local/bin/ffmpeg",
        "/opt/local/bin/ffmpeg",
    ):
        if Path(candidate).is_file():
            return candidate
    return None


def find_ffprobe() -> str | None:
    bundled = bundled_binary("ffprobe")
    if bundled:
        return str(bundled)
    path = shutil.which("ffprobe")
    if path:
        return path
    for candidate in (
        "/opt/homebrew/bin/ffprobe",
        "/usr/local/bin/ffprobe",
        "/opt/local/bin/ffprobe",
    ):
        if Path(candidate).is_file():
            return candidate
    return None


def is_video_file(path: Path) -> bool:
    return path.suffix.lower() in VIDEO_EXTENSIONS


def build_output_path(source: Path, index: int) -> Path:
    stem = source.stem
    suffix = source.suffix or ".mp4"
    return source.parent / f"{stem}_指纹_{index:03d}{suffix}"


def build_ffmpeg_command(
    ffmpeg: str,
    source: Path,
    output: Path,
    params: FingerprintParams,
) -> list[str]:
    filters: list[str] = []

    if params.pad_px > 0:
        pad_color = f"{random_pad_color(params):x}".zfill(6)
        filters.append(
            f"pad=iw+{params.pad_px * 2}:ih+{params.pad_px * 2}:"
            f"{params.pad_px}:{params.pad_px}:0x{pad_color}"
        )

    filters.append(f"scale=trunc(iw*{params.scale_factor}/2)*2:trunc(ih*{params.scale_factor}/2)*2")

    if params.crop_px > 0:
        filters.append(f"crop=iw-{params.crop_px * 2}:ih-{params.crop_px * 2}")

    if abs(params.rotate_deg) > 0.001:
        radians = params.rotate_deg * 3.14159265 / 180
        filters.append(f"rotate={radians}:c=none")

    eq_parts = [
        f"brightness={params.brightness}",
        f"contrast={params.contrast}",
        f"saturation={params.saturation}",
    ]
    filters.append("eq=" + ":".join(eq_parts))

    if abs(params.hue_shift) > 0.01:
        filters.append(f"hue=h={params.hue_shift}")

    if params.noise_strength > 0:
        filters.append(f"noise=alls={params.noise_strength}:allf=t+u")

    filters.append(f"setpts=PTS/{params.speed}")

    video_filter = ",".join(filters)
    audio_filter = f"atempo={params.speed},volume={params.audio_volume}"

    command = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-progress",
        "pipe:1",
        "-nostats",
        "-i",
        str(source),
        "-vf",
        video_filter,
        "-af",
        audio_filter,
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        str(params.crf),
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-movflags",
        "+faststart",
        "-metadata",
        f"title={params.metadata_title}",
        "-metadata",
        f"comment={params.metadata_comment}",
        "-metadata",
        f"encoder={params.metadata_encoder}",
        str(output),
    ]
    return command


def random_pad_color(params: FingerprintParams) -> int:
    seed = sum(ord(c) for c in params.metadata_title)
    r = (seed * 17) % 8
    g = (seed * 31) % 8
    b = (seed * 47) % 8
    return (r << 16) | (g << 8) | b


def parse_ffmpeg_progress(line: str, duration_ms: float | None) -> float | None:
    if line.startswith("out_time_ms=") and duration_ms:
        try:
            out_ms = float(line.split("=", 1)[1].strip())
            if duration_ms > 0:
                return min(out_ms / duration_ms, 1.0)
        except ValueError:
            return None
    return None


def probe_duration_ms(ffmpeg: str, source: Path) -> float | None:
    ffprobe = find_ffprobe()
    if not ffprobe:
        fallback = ffmpeg.replace("ffmpeg", "ffprobe")
        if Path(fallback).is_file():
            ffprobe = fallback
        else:
            return None

    command = [
        ffprobe,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(source),
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        seconds = float(result.stdout.strip())
        return seconds * 1_000_000
    except (subprocess.CalledProcessError, ValueError):
        return None


ProgressCallback = Callable[[int, int, float, str], None]
CancelCallback = Callable[[], bool]


def process_videos(
    source_path: str,
    count: int,
    on_progress: ProgressCallback | None = None,
    should_cancel: CancelCallback | None = None,
) -> list[str]:
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        raise RuntimeError("未找到 FFmpeg，请先安装：brew install ffmpeg")

    source = Path(source_path).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"找不到视频文件：{source}")
    if not is_video_file(source):
        raise ValueError("不支持的文件格式，请拖入常见视频文件（mp4/mov/mkv 等）")

    fingerprints = generate_fingerprints(str(source), count)
    outputs: list[str] = []
    duration_ms = probe_duration_ms(ffmpeg, source)

    for index, params in enumerate(fingerprints, start=1):
        if should_cancel and should_cancel():
            break

        output = build_output_path(source, index)
        command = build_ffmpeg_command(ffmpeg, source, output, params)

        if on_progress:
            on_progress(index, count, 0.0, f"正在生成第 {index}/{count} 个视频…")

        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

        assert process.stdout is not None
        for line in process.stdout:
            if should_cancel and should_cancel():
                process.terminate()
                break
            progress = parse_ffmpeg_progress(line.strip(), duration_ms)
            if progress is not None and on_progress:
                overall = ((index - 1) + progress) / count
                on_progress(index, count, overall, f"正在生成第 {index}/{count} 个视频…")

        process.wait()
        if process.returncode != 0:
            stderr = process.stderr.read() if process.stderr else ""
            raise RuntimeError(f"第 {index} 个视频生成失败：{stderr.strip() or '未知错误'}")

        outputs.append(str(output))

        if on_progress:
            on_progress(index, count, index / count, f"已完成第 {index}/{count} 个")

    return outputs


def format_file_size(size_bytes: int) -> str:
    units = ["B", "KB", "MB", "GB"]
    size = float(size_bytes)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"
