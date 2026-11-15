import json
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from synth_sfx import PRESETS

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")


def duration_of(path: Path) -> float:
    result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
                            capture_output=True, text=True, check=True)
    return float(json.loads(result.stdout)["format"]["duration"])


@pytest.mark.parametrize("preset", sorted(PRESETS))
def test_preset_lands_on_peak(tmp_path: Path, run_script: Callable[..., dict[str, Any]], preset: str) -> None:
    out = run_script("synth_sfx.py", preset, "--out-dir", str(tmp_path))
    path = Path(out["audio"])
    assert path.name == f"{preset}_v1.wav"
    assert out["true_peak_dbtp"] == pytest.approx(-3.0, abs=0.5)
    assert duration_of(path) == pytest.approx(PRESETS[preset].duration_s, abs=0.05)
    record = json.loads(path.with_suffix(".gen.json").read_text())
    assert record["request"]["preset"] == preset


def test_second_run_is_a_new_take(tmp_path: Path, run_script: Callable[..., dict[str, Any]]) -> None:
    first = run_script("synth_sfx.py", "tick", "--name", "click", "--out-dir", str(tmp_path))
    second = run_script("synth_sfx.py", "tick", "--name", "click", "--out-dir", str(tmp_path))
    assert Path(first["audio"]).name == "click_v1.wav"
    assert Path(second["audio"]).name == "click_v2.wav"
    assert Path(first["audio"]).exists()
