"""Check that a preview still matches the same frame of the render.

A still is the first draw of its frame; a render reaches most frames after others. When
something is set up late (a light or texture added from an effect, a font still loading)
the two differ, and every still looks right while the render does not. This compares
`remotion still --frame=N` with frame N of the rendered video on a grid of blocks and
reports the mean difference and the worst block, in 8-bit luma levels: a whole-frame
mean hides one object that changed.

Usage: frame_diff.py STILL VIDEO --frame N [--max-block 12]
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from media import MediaError

COLUMNS, ROWS = 16, 9
SAMPLE = (320, 180)


def gray(args: list[str], what: str) -> bytes:
    """One frame as 8-bit luma at the sample size."""
    result = subprocess.run(
        ["ffmpeg", "-v", "error", *args, "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True, check=False
    )
    if result.returncode != 0 or len(result.stdout) != SAMPLE[0] * SAMPLE[1]:
        raise MediaError(f"reading {what} failed: {result.stderr.decode(errors='replace')[-800:]}")
    return result.stdout


def block_differences(a: bytes, b: bytes) -> list[float]:
    """Mean absolute luma difference of each block of the grid, row by row."""
    width, height = SAMPLE
    block_w, block_h = width // COLUMNS, height // ROWS
    sums = [0] * (COLUMNS * ROWS)
    for y in range(height):
        row = (y // block_h) * COLUMNS
        offset = y * width
        for x in range(width):
            sums[row + x // block_w] += abs(a[offset + x] - b[offset + x])
    return [total / (block_w * block_h) for total in sums]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("still", type=Path)
    parser.add_argument("video", type=Path)
    parser.add_argument("--frame", type=int, required=True, help="frame number the still was rendered at")
    parser.add_argument("--max-block", type=float, default=12.0, help="warn when the worst block differs by more than this many levels (video compression alone gives about 5)")
    args = parser.parse_args()

    scale = f"scale={SAMPLE[0]}:{SAMPLE[1]}:flags=area"
    still = gray(["-i", str(args.still), "-vf", scale], str(args.still))
    rendered = gray(["-i", str(args.video), "-map", "0:v:0", "-vf", f"select=eq(n\\,{args.frame}),{scale}"], f"frame {args.frame} of {args.video}")
    blocks = block_differences(still, rendered)
    worst = max(range(len(blocks)), key=lambda index: blocks[index])
    report = {
        "frame": args.frame,
        "mean_difference": round(sum(blocks) / len(blocks), 2),
        "worst_block": {"difference": round(blocks[worst], 2), "column": worst % COLUMNS, "row": worst // COLUMNS, "grid": f"{COLUMNS}x{ROWS}"},
        "warnings": [],
    }
    if blocks[worst] > args.max_block:
        report["warnings"].append(
            f"the still and the render differ by {blocks[worst]:.1f} levels in block column {worst % COLUMNS}, row {worst // COLUMNS}: "
            "something reaches the frame late (set from an effect, or still loading)"
        )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
