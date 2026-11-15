"""Normalise a render's loudness for delivery (two-pass loudnorm, picture copied untouched).

Defaults suit YouTube and social video: -14 LUFS integrated, -1 dBTP true peak.
Use --target -16 for podcasts and -23 for broadcast. Refuses to overwrite: a delivered
version is never replaced. --replace is only for an export nobody has been sent yet,
when a review after exporting found something to fix.

loudnorm is asked for linear mode (one gain for the whole file), but ffmpeg falls back to
dynamic mode, which rides the gain and can pump or miss the target, when the gain would
push peaks over the ceiling or the loudness range is wider than --lra. The report says
which mode ran and why. --limit replaces loudnorm with one gain plus a peak limiter, the
usual master for peaky speech, and reports how many dB the limiter took off.

Usage: loudnorm_export.py INPUT OUTPUT [--target -14] [--true-peak -1.0] [--lra 11] [--limit] [--replace]
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from media import measure_loudness, run

MEASURED_KEYS = ("input_i", "input_tp", "input_lra", "input_thresh", "target_offset")
# Peak overshoot loudnorm may smooth in dynamic mode without warning: two of this skill's
# own renders went dynamic for 1.0 and 1.2 dB and still landed on target.
PEAK_OVERSHOOT_OK_DB = 2.0
LOUDNESS_TOLERANCE_LU = 1.0
# The limiter works on sample peaks at 4x oversampling; this margin keeps the true peak of
# the encoded AAC under the ceiling.
LIMIT_MARGIN_DB = 0.5
LIMIT_PASSES = 4


@dataclass(frozen=True)
class Blocker:
    """One reason loudnorm cannot apply a single linear gain: ``amount`` dB (peaks) or LU (range) over."""

    cause: str
    amount: float


def parse_loudnorm_json(stderr: str) -> dict[str, str]:
    """loudnorm prints one JSON object near the end of stderr (an encoder may log after it)."""
    start = stderr.rfind("{")
    if start == -1:
        raise ValueError("loudnorm printed no measurement")
    return json.loads(stderr[start:stderr.rfind("}") + 1])


def parse_measurement(stderr: str) -> dict[str, str]:
    measured = parse_loudnorm_json(stderr)
    missing = [key for key in MEASURED_KEYS if key not in measured]
    if missing:
        raise ValueError(f"loudnorm measurement is missing {missing}")
    return measured


def linear_blockers(measured: dict[str, str], *, target_i: float, target_tp: float, target_lra: float) -> list[Blocker]:
    """Why ffmpeg will refuse linear mode: peaks the gain lifts over the ceiling, or too wide a range."""
    blockers: list[Blocker] = []
    overshoot = float(measured["input_tp"]) + (target_i - float(measured["input_i"])) - target_tp
    if overshoot > 0:
        blockers.append(Blocker("peaks", round(overshoot, 2)))
    excess_range = float(measured["input_lra"]) - target_lra
    if excess_range > 0:
        blockers.append(Blocker("range", round(excess_range, 2)))
    return blockers


def dynamic_warnings(blockers: list[Blocker], measured: dict[str, str], args: argparse.Namespace) -> list[str]:
    warnings: list[str] = []
    for blocker in blockers:
        if blocker.cause == "peaks" and blocker.amount > PEAK_OVERSHOOT_OK_DB:
            ratio = float(measured["input_tp"]) - float(measured["input_i"])
            warnings.append(
                f"loudnorm ran in dynamic mode: at {args.target} LUFS the peaks would land {blocker.amount:.1f} dB over "
                f"{args.true_peak} dBTP (peaks sit {ratio:.1f} dB above the loudness; {args.true_peak - args.target:.1f} dB fits). "
                "Dynamic mode rides the gain and can pump: re-export with --limit and report how much the limiter took off"
            )
        if blocker.cause == "range":
            warnings.append(
                f"loudnorm ran in dynamic mode: the loudness range is {measured['input_lra']} LU, over the {args.lra} LU target. "
                "Find the uneven part with probe.py --timeline and fix the mix, or pass a wider --lra if the range is meant"
            )
    if not blockers and float(measured["input_lra"]) == 0:
        warnings.append("loudnorm ran in dynamic mode because the source measures a loudness range of 0 "
                        "(a perfectly steady tone or near silence), which it will not normalise linearly")
    elif not blockers:
        warnings.append("loudnorm ran in dynamic mode for a reason this script cannot name; check the export by ear and on meters")
    return warnings


def limit_filter(gain_db: float, ceiling_dbfs: float) -> str:
    return (
        f"aresample=192000,volume={gain_db:.3f}dB,"
        f"alimiter=limit={10 ** (ceiling_dbfs / 20):.5f}:level=false:attack=0.5:release=40,aresample=48000"
    )


def find_limit_gain(source: Path, measured: dict[str, str], target: float, ceiling: float) -> float:
    """The gain that lands on ``target`` after limiting: limiting peaks also lowers loudness, so iterate."""
    gain = target - float(measured["input_i"])
    with tempfile.TemporaryDirectory() as scratch:
        trial = Path(scratch) / "trial.wav"
        for _ in range(LIMIT_PASSES):
            run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(source), "-map", "0:a:0",
                 "-af", limit_filter(gain, ceiling), "-c:a", "pcm_f32le", str(trial)])
            level = measure_loudness(trial)
            if level is None:
                raise ValueError(f"{source} measured silent after limiting")
            miss = target - level.integrated_lufs
            if abs(miss) <= 0.2:
                break
            gain += miss
    return gain


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--target", type=float, default=-14.0, help="integrated loudness, LUFS")
    parser.add_argument("--true-peak", type=float, default=-1.0, help="ceiling, dBTP")
    parser.add_argument("--lra", type=float, default=11.0, help="loudness range target, LU")
    parser.add_argument("--limit", action="store_true", help="one gain plus a peak limiter instead of loudnorm")
    parser.add_argument("--replace", action="store_true", help="overwrite an export that has not been sent to anyone")
    args = parser.parse_args()
    if args.output.exists() and not args.replace:
        sys.exit(f"{args.output} exists; choose a new name (versions are never overwritten), or --replace if it was never sent")

    targets = f"I={args.target}:TP={args.true_peak}:LRA={args.lra}"
    first = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(args.input), "-map", "0:a:0",
                 "-af", f"loudnorm={targets}:print_format=json", "-f", "null", "-"])
    measured = parse_measurement(first.stderr)
    blockers = linear_blockers(measured, target_i=args.target, target_tp=args.true_peak, target_lra=args.lra)

    limiter_db: float | None = None
    if args.limit:
        ceiling = args.true_peak - LIMIT_MARGIN_DB
        gain = find_limit_gain(args.input, measured, args.target, ceiling)
        audio_filter = limit_filter(gain, ceiling)
        limiter_db = round(max(0.0, float(measured["input_tp"]) + gain - ceiling), 1)
    else:
        audio_filter = (
            f"loudnorm={targets}:measured_I={measured['input_i']}:measured_TP={measured['input_tp']}"
            f":measured_LRA={measured['input_lra']}:measured_thresh={measured['input_thresh']}"
            f":offset={measured['target_offset']}:linear=true:print_format=json"
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    second = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(args.input),
                  "-map", "0:v:0?", "-map", "0:a:0", "-c:v", "copy", "-af", audio_filter,
                  "-c:a", "aac", "-b:a", "320k", "-ar", "48000", "-movflags", "+faststart",
                  *(["-y"] if args.replace else []), str(args.output)])
    mode = "limit" if args.limit else parse_loudnorm_json(second.stderr)["normalization_type"]

    warnings = dynamic_warnings(blockers, measured, args) if mode == "dynamic" else []
    if mode == "limit" and any(b.cause == "range" for b in blockers):
        warnings.append(f"the loudness range is {measured['input_lra']} LU, over the {args.lra} LU target, and a limiter "
                        "does not even it out: find the uneven part with probe.py --timeline and fix the mix")
    result = measure_loudness(args.output)
    if result is not None:
        if abs(result.integrated_lufs - args.target) > LOUDNESS_TOLERANCE_LU:
            warnings.append(f"the export measures {result.integrated_lufs} LUFS, more than {LOUDNESS_TOLERANCE_LU} LU off {args.target}")
        if result.true_peak_dbtp > args.true_peak:
            warnings.append(f"the export peaks at {result.true_peak_dbtp} dBTP, over the {args.true_peak} dBTP ceiling")
    print(json.dumps({
        "output": str(args.output),
        "normalization_type": mode,
        "blockers": [{"cause": b.cause, "amount": b.amount} for b in blockers],
        "limiter_db": limiter_db,
        "before": {"integrated_lufs": float(measured["input_i"]), "true_peak_dbtp": float(measured["input_tp"]),
                   "range_lu": float(measured["input_lra"])},
        "after": None if result is None else {
            "integrated_lufs": result.integrated_lufs, "true_peak_dbtp": result.true_peak_dbtp,
        },
        "warnings": warnings,
    }, indent=2))


if __name__ == "__main__":
    main()
