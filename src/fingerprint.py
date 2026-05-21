"""为每个输出视频生成唯一的指纹修改参数。"""

from __future__ import annotations

import hashlib
import random
import string
from dataclasses import dataclass


@dataclass(frozen=True)
class FingerprintParams:
    speed: float
    brightness: float
    contrast: float
    saturation: float
    crop_px: int
    scale_factor: float
    rotate_deg: float
    crf: int
    metadata_title: str
    metadata_comment: str
    metadata_encoder: str
    audio_volume: float
    noise_strength: int
    hue_shift: float
    pad_px: int


def _random_string(length: int, seed: int) -> str:
    rng = random.Random(seed)
    chars = string.ascii_letters + string.digits
    return "".join(rng.choice(chars) for _ in range(length))


def generate_fingerprints(source_path: str, count: int) -> list[FingerprintParams]:
    """基于源文件路径生成 count 组互不相同的参数。"""
    base_seed = int(hashlib.sha256(source_path.encode()).hexdigest(), 16) % (2**32)
    results: list[FingerprintParams] = []

    for index in range(count):
        rng = random.Random(base_seed + index * 9973)
        results.append(
            FingerprintParams(
                speed=round(rng.uniform(0.996, 1.004), 4),
                brightness=round(rng.uniform(-0.015, 0.015), 4),
                contrast=round(rng.uniform(0.985, 1.015), 4),
                saturation=round(rng.uniform(0.985, 1.015), 4),
                crop_px=rng.randint(0, 3),
                scale_factor=round(rng.uniform(0.997, 1.003), 4),
                rotate_deg=round(rng.uniform(-0.15, 0.15), 3),
                crf=rng.randint(18, 23),
                metadata_title=_random_string(rng.randint(8, 16), base_seed + index),
                metadata_comment=_random_string(rng.randint(12, 24), base_seed + index + 1),
                metadata_encoder=f"encoder-{ _random_string(6, base_seed + index + 2) }",
                audio_volume=round(rng.uniform(0.992, 1.008), 4),
                noise_strength=rng.randint(1, 4),
                hue_shift=round(rng.uniform(-2.0, 2.0), 2),
                pad_px=rng.randint(0, 2),
            )
        )

    return results
