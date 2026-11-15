"""ffmpeg/ffprobe wrappers shared by the measurement scripts."""

from __future__ import annotations

import array
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class MediaError(RuntimeError):
    """An ffmpeg or ffprobe call failed."""


def run(args: list[str]) -> subprocess.CompletedProcess[str]:
    """Run a command and return it; raise with its stderr tail if it fails."""
    if shutil.which(args[0]) is None:
        raise MediaError(f"{args[0]} not found on PATH")
    result = subprocess.run(args, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise MediaError(f"{' '.join(args[:3])} … failed ({result.returncode}): {result.stderr[-1500:]}")
    return result


def ffprobe(path: Path) -> dict[str, Any]:
    """ffprobe's JSON for a file: ``format`` and ``streams``, as ffprobe shapes them (an external payload, hence Any)."""
    result = run(
        ["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)]
    )
    return json.loads(result.stdout)


def frame_rate(rate: str) -> float:
    """Parse an ffprobe rate such as ``30000/1001``."""
    numerator, _, denominator = rate.partition("/")
    return float(numerator) / float(denominator or 1)


@dataclass(frozen=True)
class Loudness:
    integrated_lufs: float
    true_peak_dbtp: float
    range_lu: float


SUMMARY_PATTERNS = {
    "integrated_lufs": re.compile(r"I:\s+(-?[\d.]+|-inf) LUFS"),
    "range_lu": re.compile(r"LRA:\s+(-?[\d.]+) LU"),
    "true_peak_dbtp": re.compile(r"Peak:\s+(-?[\d.]+|-inf) dBFS"),
}


def parse_ebur128_summary(stderr: str) -> Loudness | None:
    """Read the summary block that ``ebur128=peak=true`` prints at the end."""
    _, found, summary = stderr.rpartition("Summary:")
    if not found:
        return None
    values: dict[str, float] = {}
    for name, pattern in SUMMARY_PATTERNS.items():
        match = pattern.search(summary)
        if match is None:
            return None
        values[name] = float(match.group(1))
    return Loudness(**values)


def measure_loudness(path: Path) -> Loudness | None:
    """Integrated loudness, true peak and range of the first audio stream, or None if silent."""
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-map", "0:a:0",
         "-af", "ebur128=peak=true", "-f", "null", "-"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return parse_ebur128_summary(result.stderr)


SHORT_TERM = re.compile(r"t:\s*([\d.]+)\s+TARGET.*?S:\s*(-?[\d.]+|-inf)")


def parse_short_term(stderr: str) -> list[tuple[float, float]]:
    """(time, short-term LUFS) for every line ``ebur128`` logs; silence (-inf, or below -70) is dropped."""
    points = [(float(t), float(s)) for t, s in SHORT_TERM.findall(stderr) if s != "-inf"]
    return [(t, s) for t, s in points if s > -70.0]


def loudness_timeline(path: Path, step_s: float = 1.0) -> list[tuple[float, float]]:
    """Short-term loudness (3 s window) of the first audio stream, sampled every ``step_s`` seconds."""
    result = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-map", "0:a:0", "-af", "ebur128", "-f", "null", "-"])
    points = parse_short_term(result.stderr)
    end = points[-1][0] if points else 0.0
    timeline: list[tuple[float, float]] = []
    for time, level in points:
        # The first full 3 s window ends at 3 s; earlier values under-read. The last
        # 2 s are left out too: most videos end on a fade, which is not unevenness.
        if 3.0 <= time <= end - 2.0 and (not timeline or time - timeline[-1][0] >= step_s - 1e-6):
            timeline.append((round(time, 1), level))
    return timeline


QUIET_TAKE_LUFS = -24.0
"""Narration takes have come back anywhere from -34 to -19 LUFS; below this one is quiet enough to plan around."""


@dataclass(frozen=True)
class TakeLevel:
    integrated_lufs: float | None
    true_peak_dbtp: float | None
    warnings: list[str]


def take_level(path: Path, *, quiet_below: float | None = None, peak_ceiling: float | None = None) -> TakeLevel:
    """Loudness and true peak of a new take, for its import summary, with warnings to act on.

    Music and effect levels are set against the narration, so a quiet take has to be
    known before they are chosen.
    """
    loudness = measure_loudness(path)
    if loudness is None:
        return TakeLevel(None, None, [f"{path.name} could not be measured (silent or unreadable)"])
    warnings: list[str] = []
    if quiet_below is not None and loudness.integrated_lufs < quiet_below:
        gain = round(-20.0 - loudness.integrated_lufs)
        warnings.append(
            f"take is quiet ({loudness.integrated_lufs} LUFS): set music and effects against it, "
            f"or play a copy raised about {gain} dB (ffmpeg -af volume={gain}dB,alimiter=limit=0.89) and record which in Decisions"
        )
    if peak_ceiling is not None and loudness.true_peak_dbtp > peak_ceiling:
        warnings.append(
            f"true peak {loudness.true_peak_dbtp} dBTP is above {peak_ceiling}: the file may be clipped; "
            "listen for distortion, and keep its level in the mix well below 0 dB"
        )
    return TakeLevel(loudness.integrated_lufs, loudness.true_peak_dbtp, warnings)


def decode_mono(path: Path, rate: int) -> array.array[int]:
    """The first audio stream as mono signed 16-bit samples at ``rate`` Hz."""
    if shutil.which("ffmpeg") is None:
        raise MediaError("ffmpeg not found on PATH")
    result = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:a:0", "-ac", "1", "-ar", str(rate), "-f", "s16le", "-"],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise MediaError(f"decoding {path} failed ({result.returncode}): {result.stderr.decode(errors='replace')[-1500:]}")
    samples = array.array("h")
    samples.frombytes(result.stdout)
    if sys.byteorder == "big":
        samples.byteswap()
    return samples


LIT_LUMA = 64
"""8-bit luma above which a pixel counts as lit (a quarter of full brightness)."""

_LIT_TABLE = bytes(1 if value > LIT_LUMA else 0 for value in range(256))


SAMPLE_FPS = 10
SAMPLE_WIDTH = 640


def pgm_frames(stream: bytes) -> list[bytes]:
    """Pixel data of each binary PGM image in a stream (``P5 <width> <height> <maxval>`` + one byte per pixel)."""
    frames: list[bytes] = []
    pos = 0
    while pos < len(stream):
        fields: list[bytes] = []
        while len(fields) < 4:
            match = re.compile(rb"\s*(\S+)").match(stream, pos)
            if match is None:
                raise MediaError(f"PGM stream is cut short at byte {pos}")
            fields.append(match.group(1))
            pos = match.end()
        if fields[0] != b"P5":
            raise MediaError(f"expected a P5 PGM frame at byte {pos}, got {fields[0][:8]!r}")
        size = int(fields[1]) * int(fields[2])
        pos += 1  # the single whitespace byte after maxval
        frames.append(stream[pos:pos + size])
        pos += size
    return frames


def lit_fractions(path: Path, start_s: float, end_s: float) -> list[tuple[float, float]]:
    """(time, share of pixels brighter than ``LIT_LUMA``) for frames sampled at ``SAMPLE_FPS`` across a stretch.

    Frames are scaled to ``SAMPLE_WIDTH`` (area-averaged) to keep long stretches cheap;
    text strokes stay lit at that size.
    """
    if shutil.which("ffmpeg") is None:
        raise MediaError("ffmpeg not found on PATH")
    result = subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", f"{start_s:.3f}", "-t", f"{max(end_s - start_s, 1 / SAMPLE_FPS):.3f}",
         "-i", str(path), "-map", "0:v:0", "-vf", f"fps={SAMPLE_FPS},scale={SAMPLE_WIDTH}:-2:flags=area,format=gray",
         "-c:v", "pgm", "-f", "image2pipe", "-"],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0 or not result.stdout:
        raise MediaError(f"reading frames {start_s:.2f}-{end_s:.2f}s of {path} failed: {result.stderr.decode(errors='replace')[-1500:]}")
    return [
        (round(start_s + index / SAMPLE_FPS, 3), frame.translate(_LIT_TABLE).count(1) / len(frame))
        for index, frame in enumerate(pgm_frames(result.stdout))
    ]


def parse_spans(stderr: str, start_key: str, end_key: str) -> list[tuple[float, float]]:
    """Pair up ``<start_key>: t`` / ``<end_key>: t`` markers from a detect filter's log."""
    starts = [float(m) for m in re.findall(rf"{start_key}[:=]\s*(-?[\d.]+)", stderr)]
    ends = [float(m) for m in re.findall(rf"{end_key}[:=]\s*(-?[\d.]+)", stderr)]
    return list(zip(starts, ends, strict=False))


def tail_change(path: Path, *, duration: float, window_s: float = 0.25) -> float | None:
    """Mean brightness change between frames (0-255, at 320 px wide and 30 fps) over the last ``window_s`` seconds.

    None when no frame pairs could be read. Measured small, so a slow drift on a hold reads
    near zero while a move still under way does not, and at a fixed rate, so the same move
    scores the same in a 30 and a 60 fps render.
    """
    result = run(
        ["ffmpeg", "-hide_banner", "-nostats", "-ss", f"{max(0.0, duration - window_s - 0.05):.3f}", "-i", str(path),
         "-map", "0:v:0", "-vf",
         "fps=30,scale=320:-2,format=gray,tblend=all_mode=difference,signalstats,metadata=print:key=lavfi.signalstats.YAVG",
         "-f", "null", "-"]
    )
    changes = [float(v) for v in re.findall(r"lavfi\.signalstats\.YAVG=([\d.]+)", result.stderr)]
    return round(sum(changes) / len(changes), 3) if changes else None


def detect_spans(path: Path, *, duration: float, still_min: float) -> dict[str, list[tuple[float, float]]]:
    """Find stretches with no visible change (stills) and black frames."""
    result = run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-map", "0:v:0",
         "-vf", f"freezedetect=n=0.001:d={still_min},blackdetect=d=0.1:pix_th=0.05",
         "-f", "null", "-"]
    )
    stills = parse_spans(result.stderr, "freeze_start", "freeze_end")
    # A still that runs to the end of the file never gets a freeze_end marker.
    open_starts = re.findall(r"freeze_start[:=]\s*(-?[\d.]+)", result.stderr)[len(stills):]
    stills += [(float(start), duration) for start in open_starts]
    black = parse_spans(result.stderr, "black_start", "black_end")
    return {"stills": stills, "black": black}
