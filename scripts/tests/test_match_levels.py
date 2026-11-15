from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from match_levels import shift_volume


@pytest.mark.parametrize(
    ("volume", "shift_db", "after"),
    [(0.09, -8.9, 0.0323), (0.5, 6.0206, 1.0), (0.32, 0.0, 0.32)],
    ids=["quieter-take", "louder-take", "same-level"],
)
def test_shift_volume(volume: float, shift_db: float, after: float) -> None:
    assert shift_volume(volume, shift_db) == pytest.approx(after, abs=1e-4)


def test_quieter_take_moves_music_and_effects_down(
    lavfi: Callable[[str, str], Path], run_script: Callable[..., dict[str, Any]]
) -> None:
    old = lavfi("aevalsrc='0.5*sin(2*PI*440*t)':s=44100:d=3", "old.wav")
    new = lavfi("aevalsrc='0.25*sin(2*PI*440*t)':s=44100:d=3", "new.wav")
    report = run_script("match_levels.py", str(old), str(new), "--db", "-9", "--volume", "0.32")
    assert report["shift_db"] == pytest.approx(-6.0, abs=0.15)
    assert report["db"][0]["after"] == pytest.approx(-15.0, abs=0.15)
    assert report["volume"][0]["after"] == pytest.approx(0.16, abs=0.005)
