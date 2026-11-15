"""probe.py --timeline, cut_frames.py, frame_diff.py, level_take.py and loudnorm_export.py --replace."""

import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from cut_frames import cut_frame, first_frames
from media import parse_short_term, take_level

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")

# 12 s of tone, `quiet_db` quieter from 6 s on.
def stepped_tone(quiet_db: float) -> str:
    return f"sine=f=440:d=12:r=48000,volume='if(lt(t,6),1,{10 ** (quiet_db / 20):.4f})':eval=frame"


@pytest.mark.parametrize(("quiet_db", "warns"), [(-12.0, True), (-2.0, False)], ids=["uneven", "even"])
def test_timeline_flags_uneven_loudness(
    lavfi: Callable[[str, str], Path], run_script: Callable[..., dict[str, Any]], quiet_db: float, warns: bool
) -> None:
    report = run_script("probe.py", str(lavfi(stepped_tone(quiet_db), "take.wav")), "--timeline")
    assert bool([w for w in report["warnings"] if w.startswith("short-term loudness spans")]) is warns
    assert (report["loudness"]["spread_lu"] > 6) is warns


def test_timeline_ignores_final_fade(lavfi: Callable[[str, str], Path], run_script: Callable[..., dict[str, Any]]) -> None:
    """A steady tone that fades out over its last 1.5 s is not uneven."""
    report = run_script("probe.py", str(lavfi("sine=f=440:d=10:r=48000,afade=t=out:st=8.5:d=1.5", "fade.wav")), "--timeline")
    assert report["loudness"]["spread_lu"] < 2
    assert not [w for w in report["warnings"] if w.startswith("short-term")]


def test_short_term_drops_silence() -> None:
    log = "[Parsed_ebur128_0 @ 0x1] t: 3.0   TARGET:-23 LUFS    M: -20.1 S: -21.5     I: -21.0 LUFS\n" \
          "[Parsed_ebur128_0 @ 0x1] t: 3.1   TARGET:-23 LUFS    M:-120.7 S:-inf     I: -21.0 LUFS\n" \
          "[Parsed_ebur128_0 @ 0x1] t: 3.2   TARGET:-23 LUFS    M:-120.7 S: -90.0     I: -21.0 LUFS\n"
    assert parse_short_term(log) == [(3.0, -21.5)]


@pytest.mark.parametrize(
    ("time", "fps", "frame"),
    [(4.35, 30, 131), (9.48, 30, 284), (13.88, 30, 416), (1.0, 30, 30), (0.5, 24, 12)],
    ids=["half-rounds-up", "fraction-under-half-rounds-down", "fraction-under-half-again", "exact", "other-rate"],
)
def test_cut_frame_matches_template_rounding(time: float, fps: float, frame: int) -> None:
    assert cut_frame(time, fps) == frame


def test_first_frames_lead_with_the_frame_before() -> None:
    assert first_frames([2.0, 0.5], 24, 2) == [[11, 12, 13], [47, 48, 49]]
    assert first_frames([0.0], 30, 2) == [[0, 1, 2]]


def cell_levels(sheet: Path, cells: int) -> list[float]:
    """Mean luma of each cell of a one-row sheet."""
    width = 160 * cells
    pixels = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(sheet), "-vf", f"scale={width}:90", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
        capture_output=True, check=True,
    ).stdout
    return [sum(pixels[row * width + cell * 160 + x] for row in range(90) for x in range(160)) / (90 * 160) for cell in range(cells)]


def test_cut_sheet_shows_the_cut_frame_second(
    tmp_path: Path, lavfi: Callable[[str, str], Path], run_script: Callable[..., dict[str, Any]]
) -> None:
    """Only frame 30 is white. A cut at 1.01 s (frame 30.3) starts on frame 30: cells are 29, 30, 31."""
    video = lavfi("color=black:s=320x180:d=2:r=30,drawbox=w=iw:h=ih:color=white:t=fill:enable='eq(n,30)'", "cut.mp4")
    sheet = tmp_path / "cuts.png"
    report = run_script("cut_frames.py", str(video), "--at", "1.01", "--frames", "2", "--cell-width", "160", "--out", str(sheet))
    assert report["rows"][0] == {"cut_frame": 30, "frames": [29, 30, 31], "first_cell": "frame before the cut"}
    before, at_cut, after = cell_levels(sheet, 3)
    assert before < 60 and after < 60
    assert at_cut > 180


def test_opening_beat_is_kept(tmp_path: Path, lavfi: Callable[[str, str], Path], run_script: Callable[..., dict[str, Any]]) -> None:
    """A beat that starts at 0 has no frame before it: its row starts on frame 0 and is still shown."""
    video = lavfi("color=black:s=320x180:d=2:r=30,drawbox=w=iw:h=ih:color=white:t=fill:enable='eq(n,0)'", "open.mp4")
    sheet = tmp_path / "cuts.png"
    report = run_script("cut_frames.py", str(video), "--at", "0", "--frames", "2", "--cell-width", "160", "--out", str(sheet))
    assert report["rows"] == [{"cut_frame": 0, "frames": [0, 1, 2], "first_cell": "cut frame"}]
    opening, second, third = cell_levels(sheet, 3)
    assert opening > 180
    assert second < 60 and third < 60


def test_cut_past_the_end_is_reported(lavfi: Callable[[str, str], Path], run_script: Callable[..., dict[str, Any]], tmp_path: Path) -> None:
    video = lavfi("color=black:s=320x180:d=1:r=30", "short.mp4")
    report = run_script("cut_frames.py", str(video), "--at", "0.2", "--at", "5", "--out", str(tmp_path / "c.png"))
    assert len(report["rows"]) == 1
    assert "past the end" in report["warnings"][0]


BASE = "color=0x808080:s=640x360:d=1:r=30"
# One box of about 2% of the frame, 60 levels brighter: an object that changed.
ONE_OBJECT = f"{BASE},drawbox=x=300:y=160:w=96:h=48:color=0xBCBCBC:t=fill"


@pytest.mark.parametrize(("still_source", "warns"), [(BASE, False), (ONE_OBJECT, True)], ids=["same", "one-object-differs"])
def test_frame_diff_sees_one_changed_object(
    lavfi: Callable[[str, str], Path], run_script: Callable[..., dict[str, Any]], still_source: str, warns: bool
) -> None:
    still = lavfi(still_source, "still.png")
    video = lavfi(BASE, "render.mp4")
    report = run_script("frame_diff.py", str(still), str(video), "--frame", "10")
    assert bool(report["warnings"]) is warns
    # The whole-frame mean stays small either way; only the worst block tells them apart.
    assert report["mean_difference"] < 3
    assert (report["worst_block"]["difference"] > 12) is warns


def test_level_take_narrows_spread_and_keeps_length(
    tmp_path: Path, lavfi: Callable[[str, str], Path], run_script: Callable[..., dict[str, Any]]
) -> None:
    take = lavfi(stepped_tone(-12.0), "narration_v1.wav")
    report = run_script("level_take.py", str(take))
    out = Path(report["audio"])
    assert out.name == "narration_v1_level.wav"
    assert report["after"]["spread_lu"] < report["before"]["spread_lu"] - 2
    assert report["after"]["true_peak_dbtp"] <= -0.9
    assert not [w for w in report["warnings"] if "length changed" in w]
    with pytest.raises(RuntimeError):  # never overwrites a levelled copy
        run_script("level_take.py", str(take))


def test_export_refuses_then_replaces(tmp_path: Path, lavfi: Callable[[str, str], Path], run_script: Callable[..., dict[str, Any]]) -> None:
    source = lavfi("sine=f=440:d=4:r=48000,volume=0.1", "render.wav")
    out = tmp_path / "delivered.m4a"
    run_script("loudnorm_export.py", str(source), str(out))
    first = out.stat().st_mtime_ns
    with pytest.raises(RuntimeError):
        run_script("loudnorm_export.py", str(source), str(out))
    assert out.stat().st_mtime_ns == first
    report = run_script("loudnorm_export.py", str(source), str(out), "--replace")
    assert report["after"]["integrated_lufs"] == pytest.approx(-14.0, abs=1.0)
    assert out.stat().st_mtime_ns > first


@pytest.mark.parametrize(
    ("volume", "quiet_warning", "peak_warning"),
    # ffmpeg's sine source peaks at -18 dBFS, so volume=8 brings it to full scale.
    [(0.3, True, False), (2.0, False, False), (8.0, False, True)],
    ids=["quiet", "normal", "full-scale"],
)
def test_take_level_warnings(lavfi: Callable[[str, str], Path], volume: float, quiet_warning: bool, peak_warning: bool) -> None:
    level = take_level(lavfi(f"sine=f=440:d=4:r=48000,volume={volume}", "take.wav"), quiet_below=-24.0, peak_ceiling=-1.0)
    assert any("take is quiet" in w for w in level.warnings) is quiet_warning
    assert any("may be clipped" in w for w in level.warnings) is peak_warning
