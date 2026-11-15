"""Save full-size PNG frames of a video at given times, for close review.

Times are seconds or ``last`` (the final frame, to check the ending settles).

Usage: extract_frame.py VIDEO TIME [TIME ...] [--out-dir out/frames]
"""

from __future__ import annotations

import argparse
from pathlib import Path

from media import run


def extract(video: Path, time: str, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    if time == "last":
        output = out_dir / f"{video.stem}_last.png"
        # -update keeps overwriting one image, so what remains is the last decoded frame.
        run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-sseof", "-0.5", "-i", str(video),
             "-update", "1", str(output)])
        return output
    seconds = float(time)
    output = out_dir / f"{video.stem}_{seconds:.3f}s.png"
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{seconds}", "-i", str(video),
         "-frames:v", "1", str(output)])
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("video", type=Path)
    parser.add_argument("times", nargs="+")
    parser.add_argument("--out-dir", type=Path, default=Path("out/frames"))
    args = parser.parse_args()
    for time in args.times:
        print(extract(args.video, time, args.out_dir))


if __name__ == "__main__":
    main()
