from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from probe import SETTLED_TAIL_CHANGE, split_by_content

BLACK = "color=black:s=640x360:d=1:r=30"
# Six 2x2 specks: decoration such as dust motes, about 0.01% of the frame.
SPECKS = ",".join(f"drawbox=x={60 + 90 * i}:y={50 + 40 * i}:w=2:h=2:color=white:t=fill" for i in range(6))
# A 120x12 block: about as much of the frame as a short caption on a dark background (0.6%).
TEXT_BLOCK = "drawbox=x=260:y=170:w=120:h=12:color=white:t=fill"


@pytest.mark.parametrize(
    ("source", "warns"),
    [(BLACK, True), (f"{BLACK},{SPECKS}", True), (f"{BLACK},{TEXT_BLOCK}", False)],
    ids=["pure-black", "black-with-specks", "dark-with-text"],
)
def test_black_warning_needs_empty_frame(
    lavfi: Callable[[str, str], Path], run_script: Callable[..., dict[str, Any]], source: str, warns: bool
) -> None:
    report = run_script("probe.py", str(lavfi(source, "clip.mp4")))
    black_warnings = [w for w in report["warnings"] if w.startswith("black frames")]
    assert bool(black_warnings) is warns
    assert bool(report["black"]) is warns
    # A dark frame with content is still listed, so the stretch can be checked by eye.
    assert bool(report["dark"]) is not warns


def test_empty_frames_around_content_still_warn(
    lavfi: Callable[[str, str], Path], run_script: Callable[..., dict[str, Any]]
) -> None:
    """One dark stretch: empty, then a caption for the middle second, then empty again."""
    source = "color=black:s=640x360:d=3:r=30,drawbox=x=260:y=170:w=120:h=12:color=white:t=fill:enable='between(t,1,2)'"
    report = run_script("probe.py", str(lavfi(source, "mixed.mp4")))
    assert report["black"] == [pytest.approx([0.0, 1.0], abs=0.15), pytest.approx([2.0, 3.0], abs=0.15)]
    assert [d["span_s"] for d in report["dark"]] == [pytest.approx([1.0, 2.0], abs=0.15)]
    assert sum(w.startswith("black frames") for w in report["warnings"]) == 2


@pytest.mark.parametrize(
    ("lits", "black", "dark"),
    [
        ([0.0, 0.0], [(0.0, 0.2)], []),
        ([0.01, 0.01], [], [[0.0, 0.2]]),
        ([0.0, 0.01, 0.01, 0.0], [(0.0, 0.1), (0.3, 0.4)], [[0.1, 0.3]]),
    ],
    ids=["all-empty", "all-content", "content-in-the-middle"],
)
def test_split_by_content(lits: list[float], black: list[tuple[float, float]], dark: list[list[float]]) -> None:
    samples = [(round(index * 0.1, 3), lit) for index, lit in enumerate(lits)]
    found_black, found_dark = split_by_content(samples, 0.0, round(len(lits) * 0.1, 3))
    assert found_black == black
    assert [entry["span_s"] for entry in found_dark] == dark


def box_moving(x_expr: str, fps: int) -> str:
    """A 40 px white square over black for 2 s, its x position given by an expression of t."""
    return (
        f"color=c=black:s=320x180:d=2:r={fps}[bg];color=c=white:s=40x40:d=2:r={fps}[fg];"
        f"[bg][fg]overlay=x='{x_expr}':y=70:shortest=1,format=yuv420p"
    )


@pytest.mark.parametrize(
    ("x_expr", "fps", "warns"),
    # 100 px/s keeps the square on screen to the end (x stays under 280).
    [("t*100", 30, True), ("t*100", 60, True), ("min(t\\,1)*200", 30, False), ("100+t*3", 30, False), ("100+t*3", 60, False)],
    ids=["still-moving", "still-moving-60fps", "settled", "slow-drift", "slow-drift-60fps"],
)
def test_last_frames_settle(
    lavfi: Callable[[str, str], Path], run_script: Callable[..., dict[str, Any]], x_expr: str, fps: int, warns: bool
) -> None:
    """Players stop on the last frame: a move still under way there is flagged at any frame rate, a slow drift is not."""
    report = run_script("probe.py", str(lavfi(box_moving(x_expr, fps), "clip.mp4")))
    assert bool([w for w in report["warnings"] if w.startswith("the last 0.25 s")]) is warns
    assert (report["last_change"] > SETTLED_TAIL_CHANGE) is warns
