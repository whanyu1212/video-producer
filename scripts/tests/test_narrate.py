"""narrate.py --dry-run: how long the read will run, and the speed that fits a target length."""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from narrate import measured_rate, read_time, speed_to_fit


def test_read_time_is_a_range() -> None:
    """300 words at 2.1-2.5 words a second: 120-143 s at the voice's own pace."""
    low, high = read_time(300, speed=1.0, rate=(2.1, 2.5))
    assert (low, high) == pytest.approx((120.0, 142.9), abs=0.1)


def test_speed_shortens_the_read() -> None:
    assert read_time(300, speed=1.1, rate=(2.1, 2.5))[1] == pytest.approx(142.9 / 1.1, abs=0.1)


@pytest.mark.parametrize(
    ("words", "target", "speed", "fits"),
    [(300, 130.0, 1.0, True), (300, 120.0, 1.1, True), (300, 80.0, 1.2, False), (300, 250.0, 0.7, False)],
    ids=["fits-as-is", "a-little-faster", "too-long", "too-short"],
)
def test_speed_to_fit(words: int, target: float, speed: float, fits: bool) -> None:
    """Speed is held to ElevenLabs' 0.7-1.2; past that the script itself has to change."""
    fit = speed_to_fit(words, target_s=target, rate=(2.1, 2.5))
    assert fit.speed == pytest.approx(speed, abs=0.05)
    assert fit.fits is fits
    assert (fit.words_to_change == 0) is fits


def test_measured_rate_from_a_take(tmp_path: Path) -> None:
    words = [{"text": f"w{i}", "start": 0.5 + i * 0.4, "end": 0.8 + i * 0.4} for i in range(21)]
    path = tmp_path / "take.words.json"
    path.write_text(json.dumps(words))
    assert measured_rate(path) == pytest.approx(21 / 8.3, abs=0.01)


def test_dry_run_reports_read_time(tmp_path: Path, run_script: Callable[..., dict[str, Any]]) -> None:
    script = tmp_path / "script.txt"
    script.write_text(" ".join(["word"] * 300))
    report = run_script("narrate.py", "--voice", "x", "--script", str(script), "--dry-run", "--target-seconds", "100")
    assert report["words"] == 300
    # 2.1-2.9 words a second by default: 103-143 s at speed 1.0, so 100 s needs a little more speed.
    assert (report["read_time_s"]["low"], report["read_time_s"]["high"]) == pytest.approx((103.4, 142.9), abs=0.1)
    assert report["fit"]["speed"] == pytest.approx(1.2, abs=0.02)


def test_dry_run_uses_the_voices_own_pace(tmp_path: Path, run_script: Callable[..., dict[str, Any]]) -> None:
    """A take read at speed 1.1 counts at its speed-1.0 pace: 11 words over 4.3 s is 2.56 a second, 2.33 at 1.0."""
    take = tmp_path / "narration_v1.words.json"
    take.write_text(json.dumps([{"text": "w", "start": i * 0.4, "end": i * 0.4 + 0.3} for i in range(11)]))
    take.with_name("narration_v1.gen.json").write_text(json.dumps({"request": {"voice_settings": {"speed": 1.1}}}))
    script = tmp_path / "script.txt"
    script.write_text(" ".join(["word"] * 250))
    report = run_script("narrate.py", "--voice", "x", "--script", str(script), "--dry-run", "--rate-from", str(take))
    pace = 11 / 4.3 / 1.1
    assert report["read_time_s"]["low"] == pytest.approx(250 / (pace * 1.05), abs=0.2)
    assert report["read_time_s"]["high"] == pytest.approx(250 / (pace * 0.95), abs=0.2)
