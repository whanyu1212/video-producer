import math
import random
import shutil
import wave
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from music_beats import nearest_beats

RATE = 22050


def write_wav(path: Path, samples: list[int]) -> Path:
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(RATE)
        out.writeframes(b"".join(int(s).to_bytes(2, "little", signed=True) for s in samples))
    return path


def click_track(bpm: float, first_beat_s: float, seconds: float, noise: random.Random) -> list[int]:
    """Quiet noise with a 15 ms noise burst on every beat."""
    samples = [noise.randint(-300, 300) for _ in range(int(seconds * RATE))]
    beat = first_beat_s
    while beat < seconds:
        start = int(beat * RATE)
        for offset in range(int(0.015 * RATE)):
            if start + offset < len(samples):
                samples[start + offset] = noise.randint(-20000, 20000)
        beat += 60 / bpm
    return samples


pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")


@pytest.mark.parametrize(("bpm", "first_beat_s"), [(120, 0.25), (96, 0.6)])
def test_finds_tempo_and_phase(tmp_path: Path, run_script: Callable[..., dict[str, Any]], bpm: float, first_beat_s: float) -> None:
    path = write_wav(tmp_path / "clicks.wav", click_track(bpm, first_beat_s, 12, random.Random(3)))
    report = run_script("music_beats.py", str(path), "--near", "5.0")
    assert report["bpm"] == pytest.approx(bpm, abs=1)
    assert report["first_beat_s"] == pytest.approx(first_beat_s, abs=0.03)
    assert report["confidence"] >= 2
    assert abs(report["near"][0]["off_s"]) <= 60 / bpm / 2


def test_no_grid_without_a_beat(tmp_path: Path, run_script: Callable[..., dict[str, Any]]) -> None:
    noise = random.Random(5)
    path = write_wav(tmp_path / "noise.wav", [noise.randint(-8000, 8000) for _ in range(10 * RATE)])
    report = run_script("music_beats.py", str(path))
    assert "beats" not in report
    assert report["warnings"] and "no grid" in report["warnings"][0]


def test_no_grid_from_one_attack(tmp_path: Path, run_script: Callable[..., dict[str, Any]]) -> None:
    """A steady tone after one fade-in has a single onset; one onset is not a beat."""
    tone = [int(12000 * min(1.0, i / (0.1 * RATE)) * math.sin(2 * math.pi * 440 * i / RATE)) for i in range(10 * RATE)]
    report = run_script("music_beats.py", str(write_wav(tmp_path / "tone.wav", tone)))
    assert "beats" not in report
    assert report["warnings"]


def test_no_grid_from_speech_like_bursts(tmp_path: Path, run_script: Callable[..., dict[str, Any]]) -> None:
    """Bursts at irregular gaps, like syllables: plenty of onsets, no steady beat."""
    rng = random.Random(11)
    samples = [rng.randint(-200, 200) for _ in range(15 * RATE)]
    at = 0.3
    while at < 14.5:
        for offset in range(int(rng.uniform(0.08, 0.25) * RATE)):
            samples[int(at * RATE) + offset] = rng.randint(-12000, 12000)
        at += rng.uniform(0.25, 0.9)
    report = run_script("music_beats.py", str(write_wav(tmp_path / "speech.wav", samples)))
    assert "beats" not in report


def test_nearest_beat_and_offset() -> None:
    assert nearest_beats([0.5, 1.0, 1.5], [1.12, 0.1]) == [
        {"near_s": 1.12, "beat_s": 1.0, "off_s": -0.12},
        {"near_s": 0.1, "beat_s": 0.5, "off_s": 0.4},
    ]
