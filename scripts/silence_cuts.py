"""Find cut points in measured silence near given times of a narration take.

To pace a take without a retake, play it as slices and insert pauses between
them (see PAUSES in a project's src/timeline.ts). A cut must sit in silence or
it clips a breath or a word. For each approximate time (--at) or word end
(--after, with the take's .words.json) this returns the nearest stretch of at
least --min-silence seconds whose level, as RMS over 50 ms, stays at or below
--threshold dBFS, and its midpoint as the cut. (ffmpeg's silencedetect judges
single samples, and the noise floor of a generated mp3 rarely stays under
-60 dB sample by sample, so it finds nothing there.)

Also reports `noise_floor_db`, the level of the take's quietest 5% of windows. When it
sits within 3 dB of --threshold (a take with audible hiss), almost nothing counts as
silence and the cuts land far from where they were asked; a warning then gives a
threshold 8 dB above the floor to retry with.

Also reports `speech_end_s`, where the trailing quiet starts; with
--threshold -35 that is the end of speech for DURATION_SECONDS (the last word's
`end` in .words.json overshoots it).

Usage: silence_cuts.py AUDIO [--at SECONDS]... [--after WORD[:NTH]]... [--words WORDS_JSON]
                       [--threshold -60] [--min-silence 0.05] [--max-off 0.5]
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import sys
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

from check_cues import load_words, normalize
from media import decode_mono
from narrate import Word

RATE = 16000
FLOOR_PERCENTILE = 0.05
# A floor this close to the threshold leaves no silence to cut in; retry this far above it.
FLOOR_MARGIN_DB = 3.0
RETRY_ABOVE_FLOOR_DB = 8.0
WINDOW_S = 0.05
HOP_S = 0.01
FULL_SCALE = 32768

Span = tuple[float, float]


def rms_levels(samples: Sequence[int], rate: int, window_s: float = WINDOW_S, hop_s: float = HOP_S) -> list[float]:
    """RMS level in dBFS of a ``window_s`` window centred on every ``hop_s`` step."""
    squares = list(itertools.accumulate((s * s for s in samples), initial=0))
    hop, half = round(hop_s * rate), round(window_s * rate / 2)
    levels = []
    for centre in range(0, len(samples), hop):
        lo, hi = max(0, centre - half), min(len(samples), centre + half)
        mean = (squares[hi] - squares[lo]) / (hi - lo)
        levels.append(10 * math.log10(max(mean, 1e-12) / FULL_SCALE**2))
    return levels


def quiet_spans(levels: list[float], threshold_db: float, min_len_s: float, hop_s: float = HOP_S) -> list[Span]:
    """Stretches of at least ``min_len_s`` where every level is at or below ``threshold_db``."""
    spans: list[Span] = []
    start: int | None = None
    for index, level in enumerate([*levels, math.inf]):
        if level <= threshold_db and start is None:
            start = index
        elif level > threshold_db and start is not None:
            if (index - start) * hop_s >= min_len_s - 1e-9:
                spans.append((round(start * hop_s, 3), round(min(index, len(levels)) * hop_s, 3)))
            start = None
    return spans


def noise_floor(levels: list[float]) -> float:
    """The level of the quietest ``FLOOR_PERCENTILE`` of windows: the take's hiss between words."""
    ordered = sorted(levels)
    return ordered[int(len(ordered) * FLOOR_PERCENTILE)] if ordered else -math.inf


@dataclass(frozen=True)
class Cut:
    near_s: float
    cut_s: float
    silence_s: Span
    off_s: float


def nearest_cut(spans: list[Span], near: float) -> Cut | None:
    """The silence closest to ``near`` (0 s away when inside it), cut at its midpoint."""
    if not spans:
        return None
    start, end = min(spans, key=lambda span: max(span[0] - near, near - span[1], 0.0))
    cut = (start + end) / 2
    return Cut(round(near, 3), round(cut, 3), (start, end), round(cut - near, 3))


def parse_word_ref(ref: str) -> tuple[str, int]:
    """``word`` or ``word:nth`` (0-based, as cue() takes it)."""
    word, sep, nth = ref.rpartition(":")
    if sep and nth.isdigit():
        return word, int(nth)
    return ref, 0


def word_ends(words: list[Word], refs: list[str]) -> tuple[list[tuple[str, float]], list[str]]:
    """End time of each ``word[:nth]`` reference, and a warning for each one not spoken."""
    ends: list[tuple[str, float]] = []
    warnings: list[str] = []
    for ref in refs:
        word, nth = parse_word_ref(ref)
        matches = [w for w in words if normalize(w.text) == normalize(word)]
        if nth < len(matches):
            ends.append((ref, matches[nth].end))
        else:
            warnings.append(f"'{word}' occurrence {nth} is not in the take ({len(matches)} found)")
    return ends, warnings


def place_cuts(
    spans: list[Span], asked: list[tuple[str | None, float]], max_off: float
) -> tuple[list[dict[str, object]], list[str]]:
    """The nearest cut for each (word or None, time) asked, in time order, with warnings for far or missing ones."""
    cuts: list[dict[str, object]] = []
    warnings: list[str] = []
    for word, near in sorted(asked, key=lambda item: item[1]):
        cut = nearest_cut(spans, near)
        label = f"after '{word}'" if word else f"{near}s"
        if cut is None:
            warnings.append(f"no silence in the take at this threshold: nothing to cut at {label}")
            continue
        if abs(cut.off_s) > max_off:
            warnings.append(f"nearest silence to {label} is {cut.off_s}s away (cut at {cut.cut_s}s): check the time")
        cuts.append({"after": word, **asdict(cut)} if word else asdict(cut))
    return cuts, warnings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("audio", type=Path)
    parser.add_argument("--at", type=float, action="append", default=[], help="approximate time in the take, seconds")
    parser.add_argument("--after", action="append", default=[], metavar="WORD[:NTH]", help="cut after this word (needs --words)")
    parser.add_argument("--words", type=Path, help="the take's .words.json")
    parser.add_argument("--threshold", type=float, default=-60.0, help="silence level, dBFS RMS")
    parser.add_argument("--min-silence", type=float, default=0.05, help="shortest silence to cut in, seconds")
    parser.add_argument("--max-off", type=float, default=0.5, help="warn when the cut is further than this from the time asked")
    args = parser.parse_args()
    if args.after and not args.words:
        sys.exit("--after needs --words (the take's .words.json)")

    asked: list[tuple[str | None, float]] = [(None, t) for t in args.at]
    warnings: list[str] = []
    if args.after:
        ends, warnings = word_ends(load_words(args.words), args.after)
        asked += ends

    samples = decode_mono(args.audio, RATE)
    duration = len(samples) / RATE
    levels = rms_levels(samples, RATE)
    floor = noise_floor(levels)
    if floor > args.threshold - FLOOR_MARGIN_DB:
        warnings.append(
            f"the take's noise floor is {floor:.1f} dBFS, within {FLOOR_MARGIN_DB:.0f} dB of --threshold {args.threshold:g}, "
            f"so little of it counts as silence: retry with --threshold {round(floor + RETRY_ABOVE_FLOOR_DB)} "
            "and check each cut falls between the words"
        )
    spans = quiet_spans(levels, args.threshold, args.min_silence)
    trailing = spans[-1][0] if spans and spans[-1][1] >= duration - HOP_S else duration
    cuts, cut_warnings = place_cuts(spans, asked, args.max_off)
    warnings += cut_warnings

    print(json.dumps({
        "file": str(args.audio),
        "duration_s": round(duration, 3),
        "threshold_db": args.threshold,
        "noise_floor_db": round(floor, 1),
        "silences": len(spans),
        "speech_end_s": round(trailing, 3),
        "cuts": cuts,
        "warnings": warnings,
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
