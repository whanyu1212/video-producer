"""Even out a narration take whose loudness drifts from line to line.

A take can read 5-6 LU louder in one sentence than another; integrated loudness hides
it and the quiet lines sink under the music. This writes a gently compressed copy
(about 2:1 above -24 dB, slow attack and release). Its overall loudness is brought back
to the original's as far as a -1 dBTP true peak allows; any remaining difference is
printed as `loudness_shift_lu`, to move music and effect levels by (match_levels.py).
Timing is untouched: the take's .words.json and pause cut points stay valid.

Opt-in. Compare `spread_lu` before and after (probe.py --timeline shows it for any
file), and listen for pumping before using the copy.

Writes, never overwriting:
  <take stem>_level.wav       the levelled copy, next to the take
  <take stem>_level.gen.json  the filter used

Usage: level_take.py TAKE
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from elevenlabs_api import write_sidecar
from media import ffprobe, loudness_timeline, measure_loudness, run

# `volume` is the level the compressor assumes at the start; left at its 0 dB default
# it turns the opening words down by several dB before it settles.
COMPRESSOR = "compand=attacks=0.2:decays=1.0:points=-70/-70|-40/-34|-24/-21|-12/-15|0/-9:volume=-20:delay=0.2"
TRUE_PEAK_CEILING = -1.0


def spread(path: Path) -> float | None:
    """Loudest minus quietest second of short-term loudness, in LU."""
    levels = [level for _, level in loudness_timeline(path)]
    return round(max(levels) - min(levels), 1) if levels else None


def render(take: Path, out: Path, gain_db: float) -> None:
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(take), "-map", "0:a:0",
         "-af", f"{COMPRESSOR},volume={gain_db:.2f}dB", "-ar", "48000", "-c:a", "pcm_s24le", str(out)])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("take", type=Path)
    args = parser.parse_args()
    out = args.take.with_name(f"{args.take.stem}_level.wav")
    if out.exists():
        sys.exit(f"{out} exists; remove it first if the take changed")
    before = measure_loudness(args.take)
    if before is None:
        sys.exit(f"{args.take} could not be measured (silent or unreadable)")

    # Two passes: compress, measure, then add the gain that restores the take's loudness,
    # held back so the true peak stays under the ceiling.
    render(args.take, out, 0.0)
    compressed = measure_loudness(out)
    if compressed is None:
        out.unlink()
        sys.exit(f"the compressed copy of {args.take} could not be measured")
    gain = min(before.integrated_lufs - compressed.integrated_lufs, TRUE_PEAK_CEILING - compressed.true_peak_dbtp)
    render(args.take, out, gain)
    after = measure_loudness(out)
    write_sidecar(out, tool="level_take", request={"take": args.take.name, "filter": COMPRESSOR, "gain_db": round(gain, 2)}, credits_estimate=0)

    drift = abs(float(ffprobe(out)["format"]["duration"]) - float(ffprobe(args.take)["format"]["duration"]))
    shift = round(after.integrated_lufs - before.integrated_lufs, 1) if after else None
    warnings = []
    if shift is not None and abs(shift) >= 0.5:
        warnings.append(f"the copy is {shift} LU from the take (true peak held at {TRUE_PEAK_CEILING} dBTP): move music and effect levels with match_levels.py")
    if drift > 0.02:
        warnings.append(f"length changed by {drift:.3f}s: word timings no longer match, do not use this copy")
    print(json.dumps({
        "audio": str(out),
        "before": {"integrated_lufs": before.integrated_lufs, "spread_lu": spread(args.take)},
        "after": {"integrated_lufs": after.integrated_lufs if after else None, "true_peak_dbtp": after.true_peak_dbtp if after else None, "spread_lu": spread(out)},
        "loudness_shift_lu": shift,
        "warnings": warnings,
    }, indent=2))


if __name__ == "__main__":
    main()
