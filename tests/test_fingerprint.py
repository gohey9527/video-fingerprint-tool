from __future__ import annotations

from dataclasses import asdict

from fingerprint import generate_fingerprints


def test_generate_fingerprints_returns_requested_count() -> None:
    results = generate_fingerprints("/tmp/example.mp4", 5)
    assert len(results) == 5


def test_generate_fingerprints_is_deterministic_for_same_source() -> None:
    first = generate_fingerprints("/tmp/stable.mp4", 3)
    second = generate_fingerprints("/tmp/stable.mp4", 3)
    assert [asdict(item) for item in first] == [asdict(item) for item in second]


def test_generate_fingerprints_differs_by_source_path() -> None:
    a = generate_fingerprints("/tmp/video-a.mp4", 1)[0]
    b = generate_fingerprints("/tmp/video-b.mp4", 1)[0]
    assert asdict(a) != asdict(b)


def test_generate_fingerprints_produces_unique_entries() -> None:
    results = generate_fingerprints("/tmp/unique.mp4", 10)
    serialized = [asdict(item) for item in results]
    assert len(serialized) == len(set(map(str, serialized)))
