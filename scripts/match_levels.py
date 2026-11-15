"""Work out how far to move music and effects when a new narration take replaces an old one.

Takes from different voices differ in loudness (a calm read can sit ~9 dB
below a bright one). Measures both takes' integrated loudness and prints the
shift, plus the new value of every level you pass: dB levels (music `baseDb`)
move by the shift, linear volumes (effects' `volume`) scale by 10^(shift/20),
so speech keeps the same lead over the music and effects.

Usage: match_levels.py OLD_TAKE NEW_TAKE [--db LEVEL]... [--volume GAIN]...
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from media import measure_loudness


def shift_volume(volume: float, shift_db: float) -> float:
    """A linear gain moved by ``shift_db`` decibels."""
    return volume * 10 ** (shift_db / 20)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("old", type=Path, help="the take the current levels were set for")
    parser.add_argument("new", type=Path, help="the take replacing it")
    parser.add_argument("--db", type=float, action="append", default=[], help="a level in dB, such as music baseDb")
    parser.add_argument("--volume", type=float, action="append", default=[], help="a linear volume, such as an effect's")
    args = parser.parse_args()

    measured = {}
    for which, path in (("old", args.old), ("new", args.new)):
        loudness = measure_loudness(path)
        if loudness is None:
            sys.exit(f"Could not measure the loudness of {path} (no audio stream, silent or unreadable)")
        measured[which] = {"file": str(path), "integrated_lufs": loudness.integrated_lufs}
    shift = round(measured["new"]["integrated_lufs"] - measured["old"]["integrated_lufs"], 1)

    print(json.dumps({
        **measured,
        "shift_db": shift,
        "db": [{"before": level, "after": round(level + shift, 1)} for level in args.db],
        "volume": [{"before": volume, "after": round(shift_volume(volume, shift), 4)} for volume in args.volume],
    }, indent=2))


if __name__ == "__main__":
    main()
