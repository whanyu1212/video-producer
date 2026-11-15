"""Tile evenly spaced frames of a video into contact sheets for visual review.

Prints JSON with each sheet's path and the approximate time of every cell
(row by row, left to right).

Usage: contact_sheet.py VIDEO [--every SECONDS] [--cols 5] [--rows 4] [--width 384] [--out-dir out/sheets]
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from media import ffprobe, run


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("video", type=Path)
    parser.add_argument("--every", type=float, help="seconds between frames (default: one sheet for the whole video)")
    parser.add_argument("--cols", type=int, default=5)
    parser.add_argument("--rows", type=int, default=4)
    parser.add_argument("--width", type=int, default=384, help="width of each cell in pixels")
    parser.add_argument("--out-dir", type=Path, default=Path("out/sheets"))
    args = parser.parse_args()

    duration = float(ffprobe(args.video)["format"]["duration"])
    cells = args.cols * args.rows
    every = args.every or duration / cells
    # Sample the middle of each interval so the first cell is not a fade-in from black.
    times = [round(every * (i + 0.5), 2) for i in range(math.ceil(duration / every)) if every * (i + 0.5) < duration]

    args.out_dir.mkdir(parents=True, exist_ok=True)
    pattern = args.out_dir / f"{args.video.stem}_sheet_%02d.png"
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(args.video),
        "-vf", f"fps=1/{every}:start_time={every / 2},scale={args.width}:-2,tile={args.cols}x{args.rows}:padding=6:margin=6:color=0x555555",
        "-fps_mode", "vfr", str(pattern),
    ])
    sheets = [
        {"path": str(args.out_dir / f"{args.video.stem}_sheet_{n + 1:02d}.png"), "times_s": times[n * cells:(n + 1) * cells]}
        for n in range(math.ceil(len(times) / cells))
    ]
    print(json.dumps({"every_s": round(every, 3), "sheets": sheets}, indent=2))


if __name__ == "__main__":
    main()
