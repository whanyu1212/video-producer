"""Find the beat grid of a music bed, so cuts meant for the beat can land on it.

Measures an onset envelope (rises in short-term energy every 10 ms), picks the tempo
whose period repeats most strongly in it (--min-bpm to --max-bpm), then the phase that
puts the most onset energy on the grid. Assumes a steady tempo, as generated beds have.

`confidence` is the share of onset energy within ±40 ms of the grid, divided by the
share a random grid would catch. `support` is the share of grid beats that have an
onset of their own (one strong attack can carry `confidence` alone). Below
--min-confidence or --min-support the grid is not printed: time cuts by hand from
the music plan's section starts instead. A wrong grid is worse than none.

With --near, prints the nearest beat to each given time (a planned cut) and how far
off it is; the quality floor wants cuts meant for the beat within 0.1 s.

Usage: music_beats.py MUSIC [--near SECONDS]... [--min-bpm 70] [--max-bpm 180]
                       [--min-confidence 2] [--min-support 0.5]
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from media import decode_mono
from silence_cuts import rms_levels

RATE = 22050
HOP_S = 0.01
WINDOW_S = 0.025
HIT_WINDOW_S = 0.04
BASELINE_S = 0.5
# A beat counts as supported when its window holds an onset at least this share of a
# strong onset (the envelope's 99th percentile) and at least MIN_ONSET_DB: a steady tone's
# window-to-window jitter rises about 0.005 dB, a generated bed's quietest beat 0.7 dB.
SUPPORT_SHARE = 0.15
MIN_ONSET_DB = 0.5
FLOOR_DB = -90.0


def onset_envelope(samples: Sequence[int], rate: int, hop_s: float = HOP_S, window_s: float = WINDOW_S) -> list[float]:
    """Rises in level (dB), every ``hop_s``, with the slow local level subtracted and negatives dropped.

    Levels come from centred windows, so a rise is dated where it happens, and are floored
    so the step out of digital silence does not outweigh every beat.
    """
    levels = [max(level, FLOOR_DB) for level in rms_levels(samples, rate, window_s, hop_s)]
    rises = [0.0, *(max(0.0, b - a) for a, b in itertools.pairwise(levels))]
    half = max(1, round(BASELINE_S / hop_s / 2))
    running = list(itertools.accumulate(rises, initial=0.0))
    envelope = []
    for index, value in enumerate(rises):
        lo, hi = max(0, index - half), min(len(rises), index + half + 1)
        envelope.append(max(0.0, value - (running[hi] - running[lo]) / (hi - lo)))
    return envelope


def autocorrelation(envelope: Sequence[float], lag: int) -> float:
    pairs = len(envelope) - lag
    return sum(envelope[i] * envelope[i + lag] for i in range(pairs)) / pairs if pairs > 0 else 0.0


def best_period(envelope: Sequence[float], min_bpm: float, max_bpm: float, hop_s: float = HOP_S) -> float:
    """Beat period in hops, refined between whole lags by a parabola through the peak."""
    lags = range(max(1, math.floor(60 / max_bpm / hop_s)), math.ceil(60 / min_bpm / hop_s) + 1)
    scores = {lag: autocorrelation(envelope, lag) for lag in lags}
    lag = max(scores, key=lambda candidate: scores[candidate])
    if lag - 1 in scores and lag + 1 in scores:
        left, mid, right = scores[lag - 1], scores[lag], scores[lag + 1]
        curve = left - 2 * mid + right
        if curve < 0:
            return lag + 0.5 * (left - right) / curve
    return float(lag)


def grid_energy(envelope: Sequence[float], period: float, phase: float, reach: int) -> float:
    """Onset energy within ``reach`` hops of each grid beat."""
    total, beat = 0.0, phase
    while beat < len(envelope):
        centre = round(beat)
        total += sum(envelope[max(0, centre - reach): centre + reach + 1])
        beat += period
    return total


@dataclass(frozen=True)
class Grid:
    bpm: float
    first_beat_s: float
    period_s: float
    confidence: float
    support: float


def refine(envelope: Sequence[float], period: float, phase: float, reach: int) -> tuple[float, float]:
    """Least-squares line through the strongest onset near each grid beat: a period and phase finer than one hop.

    The autocorrelation period is only good to a fraction of a hop, and that error
    adds up over a minute of beats; the onsets themselves pin the grid down.
    """
    points: list[tuple[int, int]] = []
    index, beat = 0, phase
    while beat < len(envelope):
        lo, hi = max(0, round(beat) - reach), min(len(envelope), round(beat) + reach + 1)
        window = envelope[lo:hi]
        if window and max(window) > 0:
            points.append((index, lo + window.index(max(window))))
        index, beat = index + 1, beat + period
    if len(points) < 3:
        return period, phase
    mean_k = sum(k for k, _ in points) / len(points)
    mean_t = sum(t for _, t in points) / len(points)
    spread = sum((k - mean_k) ** 2 for k, _ in points)
    slope = sum((k - mean_k) * (t - mean_t) for k, t in points) / spread
    return slope, mean_t - slope * mean_k


def fit_grid(envelope: Sequence[float], min_bpm: float, max_bpm: float, hop_s: float = HOP_S) -> Grid:
    period = best_period(envelope, min_bpm, max_bpm, hop_s)
    reach = max(1, round(HIT_WINDOW_S / hop_s))
    phase: float = max(range(math.ceil(period)), key=lambda candidate: grid_energy(envelope, period, candidate, reach))
    for _ in range(2):
        period, phase = refine(envelope, period, phase, reach)
    phase %= period
    total = sum(envelope) or 1.0
    caught = grid_energy(envelope, period, phase, reach) / total
    chance = min(1.0, (2 * reach + 1) / period)
    return Grid(
        round(60 / (period * hop_s), 2),
        round(phase * hop_s, 3),
        period * hop_s,
        round(caught / chance, 2),
        round(beat_support(envelope, period, phase, reach), 2),
    )


def beat_support(envelope: Sequence[float], period: float, phase: float, reach: int) -> float:
    """Share of grid beats with an onset of their own within ``reach`` hops."""
    if not envelope:
        return 0.0
    needed = max(MIN_ONSET_DB, SUPPORT_SHARE * sorted(envelope)[int(0.99 * (len(envelope) - 1))])
    hits = beats = 0
    beat = phase
    while beat < len(envelope):
        centre = round(beat)
        window = envelope[max(0, centre - reach): centre + reach + 1]
        hits += bool(window) and max(window) >= needed
        beats += 1
        beat += period
    return hits / beats if beats else 0.0


def beat_times(grid: Grid, duration_s: float) -> list[float]:
    count = math.floor((duration_s - grid.first_beat_s) / grid.period_s) + 1
    return [round(grid.first_beat_s + index * grid.period_s, 3) for index in range(max(0, count))]


def nearest_beats(beats: Sequence[float], times: Sequence[float]) -> list[dict[str, float]]:
    found = []
    for time in times:
        beat = min(beats, key=lambda candidate: abs(candidate - time))
        found.append({"near_s": time, "beat_s": beat, "off_s": round(beat - time, 3)})
    return found


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("music", type=Path)
    parser.add_argument("--near", type=float, action="append", default=[], help="a planned cut time, seconds")
    parser.add_argument("--min-bpm", type=float, default=70.0)
    parser.add_argument("--max-bpm", type=float, default=180.0)
    parser.add_argument("--min-confidence", type=float, default=2.0, help="grid must catch this many times chance")
    parser.add_argument("--min-support", type=float, default=0.5, help="share of beats that need an onset of their own")
    args = parser.parse_args()

    samples = decode_mono(args.music, RATE)
    duration = len(samples) / RATE
    grid = fit_grid(onset_envelope(samples, RATE), args.min_bpm, args.max_bpm)
    report: dict[str, object] = {
        "file": str(args.music),
        "duration_s": round(duration, 3),
        "bpm": grid.bpm,
        "confidence": grid.confidence,
        "support": grid.support,
    }
    weak = [
        f"confidence {grid.confidence} < {args.min_confidence}" if grid.confidence < args.min_confidence else "",
        f"support {grid.support} < {args.min_support}" if grid.support < args.min_support else "",
    ]
    if any(weak):
        reason = ", ".join(part for part in weak if part)
        report["warnings"] = [f"weak beat ({reason}): no grid printed; time cuts by hand"]
    else:
        beats = beat_times(grid, duration)
        report |= {"first_beat_s": grid.first_beat_s, "beats": beats, "warnings": []}
        if args.near:
            report["near"] = nearest_beats(beats, args.near)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
