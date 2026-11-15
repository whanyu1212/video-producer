"""Tile the first frames after each cut, to see what every beat opens on.

A contact sheet samples a frame every second or two and probe.py only measures stills
and black, so neither shows a beat that opens on a few frames of empty background.
Give the time of each cut (the beat starts in src/timeline.ts); this writes one PNG
with a row per cut: the last frame before the cut, then the first --frames frames of
the new beat, left to right. The cut frame is round(seconds x fps), as the template's
sec() places it. Read the PNG: in every row the first cell is the old beat, and the
second already shows the new beat's content. A beat that starts at 0 has no frame
before it: its row starts on the opening frame instead (`first_cell` in the output
says which).

Usage: cut_frames.py VIDEO --at SECONDS [--at SECONDS]... [--frames 4] [--cell-width 384] [--out out/cuts.png]
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from media import ffprobe, frame_rate, run


def cut_frame(time: float, fps: float) -> int:
    """The frame a beat starting at ``time`` begins on: halves round up, like JavaScript's Math.round in sec()."""
    return math.floor(time * fps + 0.5 + 1e-9)


def first_frames(times: list[float], fps: float, count: int) -> list[list[int]]:
    """Frame numbers shown for each cut: the frame before it, then its first ``count`` frames.

    Every row has ``count + 1`` frames. A cut on frame 0 has nothing before it, so its row
    is frames 0 to ``count``.
    """
    rows = []
    for time in sorted(times):
        first = max(0, cut_frame(time, fps) - 1)
        rows.append(list(range(first, first + count + 1)))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("video", type=Path)
    parser.add_argument("--at", type=float, action="append", required=True, help="time of a cut, seconds")
    parser.add_argument("--frames", type=int, default=4, help="frames of the new beat to show")
    parser.add_argument("--cell-width", type=int, default=384)
    parser.add_argument("--out", type=Path, default=Path("out/cuts.png"))
    args = parser.parse_args()

    info = ffprobe(args.video)
    video = next(stream for stream in info["streams"] if stream["codec_type"] == "video")
    fps = frame_rate(video["avg_frame_rate"])
    total = round(float(info["format"]["duration"]) * fps)
    cuts = [cut_frame(time, fps) for time in sorted(args.at)]
    shown = list(zip(cuts, first_frames(args.at, fps, args.frames), strict=True))
    warnings = [f"cut at frame {cut} is past the end ({total} frames)" for cut, row in shown if row[-1] >= total]
    shown = [(cut, row) for cut, row in shown if row[-1] < total]
    rows = [row for _, row in shown]
    if not rows:
        parser.error("no cut lies inside the video")

    select = "+".join(f"between(n\\,{row[0]}\\,{row[-1]})" for row in rows)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(args.video), "-map", "0:v:0",
         "-vf", f"select='{select}',scale={args.cell_width}:-2,tile={args.frames + 1}x{len(rows)}",
         "-frames:v", "1", "-fps_mode", "passthrough", str(args.out)])
    print(json.dumps({"sheet": str(args.out), "fps": round(fps, 3), "rows": [{"cut_frame": cut, "frames": row, "first_cell": "cut frame" if cut == row[0] else "frame before the cut"} for cut, row in shown], "warnings": warnings}, indent=2))


if __name__ == "__main__":
    main()
