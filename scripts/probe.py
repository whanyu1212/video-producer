"""Measure a media file and flag anything that breaks the delivery rules.

Prints JSON: duration, picture, sound, loudness, still and black stretches, how much the
last 0.25 s still changes (last_change), and warnings (loudness off target, true peak
too hot, dead stills, black frames, an ending still in motion).
Black stretches are checked frame by frame (10 a second): runs whose frames still hold
content (a caption on a dark design) are listed under "dark" with their lowest lit share
instead of warning, and only the empty runs warn; check the dark ones by eye.

With --timeline it adds short-term loudness second by second and warns when the
loudest and quietest seconds are more than --max-spread LU apart: an uneven mix or take
that integrated loudness hides.

Usage: probe.py FILE [--target-lufs -14] [--still-min 0.5] [--quick] [--timeline] [--max-spread 6]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from media import detect_spans, ffprobe, frame_rate, lit_fractions, loudness_timeline, measure_loudness, tail_change

TRUE_PEAK_CEILING = -1.0
LOUDNESS_TOLERANCE_LU = 1.0
# blackdetect flags any mostly dark frame, including a caption on a dark design. A
# frame with at least this share of lit pixels holds content: short text on a dark
# backdrop measured 0.6-0.8%, dust-mote decoration about 0.01-0.05%.
CONTENT_LIT_FRACTION = 0.002
# Mean frame-to-frame change (at 30 fps) over the last 0.25 s above which the ending is
# still moving. Two of this skill's delivered intros ended on drift, a pulsing glow and
# dust at 0.14 and 0.44; two section renders another tool flagged as ending mid-move
# measured 1.53 and 1.79, and one ending on a fade-out 1.05.
SETTLED_TAIL_CHANGE = 0.8


Span = tuple[float, float]


def split_by_content(samples: list[tuple[float, float]], start: float, end: float) -> tuple[list[Span], list[dict[str, object]]]:
    """Split one dark stretch into empty runs and runs with content, from (time, lit share) samples in time order.

    Each run starts at its first sample (the stretch's start for the first run) and
    ends where the next run starts (the stretch's end for the last).
    """
    runs: list[tuple[bool, float, list[float]]] = []
    for time, lit in samples:
        has_content = lit >= CONTENT_LIT_FRACTION
        if runs and runs[-1][0] == has_content:
            runs[-1][2].append(lit)
        else:
            runs.append((has_content, time if runs else start, [lit]))
    black: list[Span] = []
    dark: list[dict[str, object]] = []
    for index, (has_content, run_start, lits) in enumerate(runs):
        run_end = runs[index + 1][1] if index + 1 < len(runs) else end
        if has_content:
            dark.append({"span_s": [round(run_start, 2), round(run_end, 2)], "lit_percent": round(min(lits) * 100, 2)})
        else:
            black.append((run_start, run_end))
    return black, dark


def split_dark_spans(path: Path, spans: list[Span]) -> tuple[list[Span], list[dict[str, object]]]:
    """Split blackdetect's spans into empty stretches and dark ones with content, judged frame by frame."""
    black: list[Span] = []
    dark: list[dict[str, object]] = []
    for start, end in spans:
        span_black, span_dark = split_by_content(lit_fractions(path, start, end), start, end)
        black += span_black
        dark += span_dark
    return black, dark


def timeline_report(path: Path, max_spread: float) -> tuple[dict[str, object], list[str]]:
    """Short-term loudness per second, its spread, and a warning when the spread is wide."""
    timeline = loudness_timeline(path)
    if not timeline:
        return {"short_term_lufs": [], "spread_lu": None}, []
    loudest = max(timeline, key=lambda point: point[1])
    quietest = min(timeline, key=lambda point: point[1])
    spread = round(loudest[1] - quietest[1], 1)
    warnings = []
    if spread > max_spread:
        warnings.append(
            f"short-term loudness spans {spread} LU ({loudest[1]} at {loudest[0]}s, {quietest[1]} at {quietest[0]}s): "
            "level the take or the mix"
        )
    return {"short_term_lufs": [[t, s] for t, s in timeline], "spread_lu": spread}, warnings


def describe(path: Path, *, target_lufs: float, still_min: float, quick: bool, timeline: bool = False, max_spread: float = 6.0) -> dict[str, object]:
    info = ffprobe(path)
    streams = info["streams"]
    # Cover art in an mp3 shows up as a video stream; it is not picture.
    video = next(
        (s for s in streams if s["codec_type"] == "video" and not s.get("disposition", {}).get("attached_pic")),
        None,
    )
    audio = next((s for s in streams if s["codec_type"] == "audio"), None)
    duration = float(info["format"]["duration"])
    report: dict[str, object] = {
        "file": str(path),
        "duration_s": round(duration, 3),
        "size_mb": round(int(info["format"]["size"]) / 1e6, 2),
    }
    warnings: list[str] = []

    if video is not None:
        fps = frame_rate(video["avg_frame_rate"])
        report["picture"] = {
            "size": f"{video['width']}x{video['height']}",
            "fps": round(fps, 3),
            "frames": round(duration * fps),
            "codec": video["codec_name"],
            "pixel_format": video.get("pix_fmt"),
        }
        if not quick:
            spans = detect_spans(path, duration=duration, still_min=still_min)
            report["stills"] = [[round(a, 2), round(b, 2)] for a, b in spans["stills"]]
            for start, end in spans["stills"]:
                warnings.append(f"still picture {start:.2f}-{end:.2f}s ({end - start:.2f}s): add motion or cut it")
            black, dark = split_dark_spans(path, spans["black"])
            report["black"] = [[round(a, 2), round(b, 2)] for a, b in black]
            report["dark"] = dark
            for start, end in black:
                warnings.append(f"black frames {start:.2f}-{end:.2f}s")
            report["last_change"] = tail_change(path, duration=duration)
            if report["last_change"] is not None and report["last_change"] > SETTLED_TAIL_CHANGE:
                warnings.append(
                    f"the last 0.25 s is still changing (mean change {report['last_change']}): players and thumbnails "
                    "stop on the last frame, so bring every element to rest, unless it is ambient drift, grain or a loop"
                )

    if audio is None:
        report["sound"] = None
    else:
        report["sound"] = {
            "codec": audio["codec_name"],
            "sample_rate": int(audio["sample_rate"]),
            "channels": audio["channels"],
        }
        loudness = measure_loudness(path)
        if loudness is None:
            warnings.append("audio stream could not be measured (silent or unreadable)")
        else:
            report["loudness"] = {
                "integrated_lufs": loudness.integrated_lufs,
                "true_peak_dbtp": loudness.true_peak_dbtp,
                "range_lu": loudness.range_lu,
                "target_lufs": target_lufs,
            }
            if abs(loudness.integrated_lufs - target_lufs) > LOUDNESS_TOLERANCE_LU:
                warnings.append(
                    f"loudness {loudness.integrated_lufs} LUFS is off the {target_lufs} target: "
                    "run loudnorm_export.py"
                )
            if loudness.true_peak_dbtp > TRUE_PEAK_CEILING:
                warnings.append(f"true peak {loudness.true_peak_dbtp} dBTP is above {TRUE_PEAK_CEILING}")
            if timeline:
                over_time, spread_warnings = timeline_report(path, max_spread)
                report["loudness"] |= over_time
                warnings += spread_warnings

    report["warnings"] = warnings
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("file", type=Path)
    parser.add_argument("--target-lufs", type=float, default=-14.0)
    parser.add_argument("--still-min", type=float, default=0.5, help="shortest still stretch to flag, seconds")
    parser.add_argument("--quick", action="store_true", help="skip the still/black scan (no full decode)")
    parser.add_argument("--timeline", action="store_true", help="add short-term loudness per second and its spread")
    parser.add_argument("--max-spread", type=float, default=6.0, help="warn when short-term loudness spans more than this, LU")
    args = parser.parse_args()
    report = describe(
        args.file, target_lufs=args.target_lufs, still_min=args.still_min, quick=args.quick,
        timeline=args.timeline, max_spread=args.max_spread,
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
