"""loudnorm_export.py: which mode ffmpeg ran, why linear was refused, and --limit."""

import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from loudnorm_export import linear_blockers

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")

# A tone whose level swells by ±3 dB: loudnorm refuses linear mode for a perfectly
# steady source (it reads a loudness range of 0), so test signals need some movement.
GENTLE = "sine=f=220:d=20:r=48000,volume='0.1*(1+0.3*sin(2*PI*0.2*t))':eval=frame"
# The same quiet tone with a full-scale click every second: speech-like peaks far above its loudness.
PEAKY = (
    "sine=f=220:d=20:r=48000,volume='0.03*(1+0.3*sin(2*PI*0.2*t))':eval=frame[a];"
    "aevalsrc=0.9*sin(2*PI*1000*t)*lt(mod(t\\,1)\\,0.004):s=48000:d=20[b];[a][b]amix=inputs=2:normalize=0"
)
# Quiet for 10 s, then 16.5 dB louder: a range wider than the 11 LU target, with low peaks.
# (A bigger step reads as a narrow range: the quiet half falls under the measurement's gate.)
WIDE = "sine=f=220:d=20:r=48000,volume='if(lt(t,10),0.03,0.2)*(1+0.3*sin(2*PI*0.2*t))':eval=frame"


@pytest.mark.parametrize(
    ("measured", "causes"),
    [
        ({"input_i": "-20", "input_tp": "-8", "input_lra": "6"}, []),
        ({"input_i": "-23.9", "input_tp": "-0.4", "input_lra": "6"}, ["peaks"]),
        ({"input_i": "-20", "input_tp": "-8", "input_lra": "14"}, ["range"]),
        ({"input_i": "-23.9", "input_tp": "-0.4", "input_lra": "14"}, ["peaks", "range"]),
    ],
    ids=["linear", "peaks", "range", "both"],
)
def test_blockers_name_each_cause(measured: dict[str, str], causes: list[str]) -> None:
    blockers = linear_blockers(measured, target_i=-14.0, target_tp=-1.0, target_lra=11.0)
    assert [b.cause for b in blockers] == causes


def test_peak_blocker_says_how_much() -> None:
    """-23.9 LUFS raised to -14 lifts a -0.4 dBTP peak to +9.5: 10.5 dB over the -1 ceiling."""
    (blocker,) = linear_blockers({"input_i": "-23.9", "input_tp": "-0.4", "input_lra": "6"}, target_i=-14.0, target_tp=-1.0, target_lra=11.0)
    assert blocker.amount == pytest.approx(10.5, abs=0.01)


@pytest.mark.parametrize(
    ("source", "mode", "warns"),
    [(GENTLE, "linear", False), (PEAKY, "dynamic", True), (WIDE, "dynamic", True)],
    ids=["gentle", "peaky", "wide"],
)
def test_export_reports_mode(
    tmp_path: Path, lavfi: Callable[[str, str], Path], run_script: Callable[..., dict[str, Any]], source: str, mode: str, warns: bool
) -> None:
    report = run_script("loudnorm_export.py", str(lavfi(source, "render.wav")), str(tmp_path / "out.m4a"))
    assert report["normalization_type"] == mode
    assert bool(report["warnings"]) is warns


def test_peaky_warning_points_at_limit(tmp_path: Path, lavfi: Callable[[str, str], Path], run_script: Callable[..., dict[str, Any]]) -> None:
    report = run_script("loudnorm_export.py", str(lavfi(PEAKY, "render.wav")), str(tmp_path / "out.m4a"))
    assert any("--limit" in w for w in report["warnings"])


def test_limit_reaches_target(tmp_path: Path, lavfi: Callable[[str, str], Path], run_script: Callable[..., dict[str, Any]]) -> None:
    """Gain plus a peak limiter lands on target where loudnorm's dynamic mode falls short."""
    report = run_script("loudnorm_export.py", str(lavfi(PEAKY, "render.wav")), str(tmp_path / "out.m4a"), "--limit")
    assert report["normalization_type"] == "limit"
    assert report["after"]["integrated_lufs"] == pytest.approx(-14.0, abs=0.5)
    assert report["after"]["true_peak_dbtp"] <= -1.0
    assert report["limiter_db"] > 5
    assert not report["warnings"]
