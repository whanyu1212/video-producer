"""Narrate a script with ElevenLabs and save the audio plus measured word timings.

Writes, never overwriting earlier takes:
  <out-dir>/<name>_vN.mp3         the narration
  <out-dir>/<name>_vN.words.json  [{"text", "start", "end"}] in seconds, for cueing animation
  <out-dir>/<name>_vN.gen.json    the request, so the take can be reproduced
Prints the take's loudness and true peak, with a warning when it is quiet: music and
effect levels are set against it.

Costs about 1 credit per character (Flash/Turbo models can be cheaper). Run with
--dry-run first to see the estimate without calling the API. The dry run also gives the
read time as a range (library voices measured 2.1-2.9 words a second at speed 1.0, pauses
included) and, with --target-seconds, the speed that fits, so a take is not paid for twice
to change its length. --rate-from a take of the same voice narrows the range to that voice.

Usage: narrate.py --voice VOICE_ID (--text TEXT | --script FILE) [--name narration]
                  [--model eleven_multilingual_v2] [--speed 1.0] [--stability 0.5] [--style 0]
                  [--seed N] [--out-dir public/assets/narration] [--dry-run]
                  [--target-seconds S] [--rate-from TAKE.words.json]
"""

from __future__ import annotations

import argparse
import base64
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from elevenlabs_api import next_take, post_json, write_sidecar
from media import QUIET_TAKE_LUFS, take_level

# Words a second at speed 1.0, pauses included: four takes by four library voices
# measured 2.11, 2.13, 2.53 and 2.85.
DEFAULT_RATE = (2.1, 2.9)
# ElevenLabs' speed setting range (eleven_v3 and eleven_v4 have none: change the words).
MIN_SPEED, MAX_SPEED = 0.7, 1.2
MEASURED_RATE_SPREAD = 0.05


@dataclass(frozen=True)
class Fit:
    """The speed that lands a script on a target length; past the speed range, words to cut (+) or add (-)."""

    speed: float
    fits: bool
    words_to_change: int


def read_time(words: int, *, speed: float, rate: tuple[float, float]) -> tuple[float, float]:
    """Shortest and longest likely read, in seconds."""
    return round(words / (rate[1] * speed), 1), round(words / (rate[0] * speed), 1)


def speed_to_fit(words: int, *, target_s: float, rate: tuple[float, float]) -> Fit:
    mid = (rate[0] + rate[1]) / 2
    wanted = words / (mid * target_s)
    speed = min(MAX_SPEED, max(MIN_SPEED, wanted))
    fits = MIN_SPEED <= wanted <= MAX_SPEED
    return Fit(round(speed, 2), fits, 0 if fits else round(words - target_s * mid * speed))


def measured_rate(words_path: Path) -> float:
    """Words a second over a take's speech, corrected to speed 1.0 when its .gen.json names a speed."""
    words = json.loads(words_path.read_text())
    rate = len(words) / (words[-1]["end"] - words[0]["start"])
    sidecar = words_path.with_name(words_path.name.removesuffix(".words.json") + ".gen.json")
    if sidecar.exists():
        settings = json.loads(sidecar.read_text()).get("request", {}).get("voice_settings", {})
        rate /= settings.get("speed", 1.0)
    return rate


@dataclass(frozen=True)
class Word:
    text: str
    start: float
    end: float


def words_from_alignment(characters: list[str], starts: list[float], ends: list[float]) -> list[Word]:
    """Collapse ElevenLabs' per-character timings into words split on whitespace."""
    words: list[Word] = []
    current: list[tuple[str, float, float]] = []
    for char, start, end in zip(characters, starts, ends, strict=True):
        if char.isspace():
            if current:
                words.append(Word("".join(c for c, _, _ in current), current[0][1], current[-1][2]))
                current = []
        else:
            current.append((char, start, end))
    if current:
        words.append(Word("".join(c for c, _, _ in current), current[0][1], current[-1][2]))
    return words


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--voice", required=True, help="ElevenLabs voice_id (find one with the ElevenLabs MCP)")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--text")
    source.add_argument("--script", type=Path, help="text file holding the narration")
    parser.add_argument("--name", default="narration")
    parser.add_argument("--model", default="eleven_multilingual_v2")
    parser.add_argument("--speed", type=float)
    parser.add_argument("--stability", type=float)
    parser.add_argument("--style", type=float)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--out-dir", type=Path, default=Path("public/assets/narration"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--target-seconds", type=float, help="dry run: the speed that lands the read on this length")
    parser.add_argument("--rate-from", type=Path, help="dry run: a .words.json take of this voice to measure its pace from")
    args = parser.parse_args()

    text = args.text if args.text is not None else args.script.read_text().strip()
    settings = {k: v for k, v in {"speed": args.speed, "stability": args.stability, "style": args.style}.items() if v is not None}
    payload: dict[str, object] = {"text": text, "model_id": args.model}
    if settings:
        payload["voice_settings"] = settings
    if args.seed is not None:
        payload["seed"] = args.seed
    credits = float(len(text))
    if args.dry_run:
        word_count = len(text.split())
        if args.rate_from is None:
            rate = DEFAULT_RATE
        else:
            measured = measured_rate(args.rate_from)
            rate = (measured * (1 - MEASURED_RATE_SPREAD), measured * (1 + MEASURED_RATE_SPREAD))
        low, high = read_time(word_count, speed=args.speed or 1.0, rate=rate)
        report: dict[str, object] = {
            "characters": len(text), "credits_estimate": credits, "voice": args.voice, "words": word_count,
            "read_time_s": {"low": low, "high": high}, "payload": payload,
        }
        if args.target_seconds is not None:
            report["fit"] = asdict(speed_to_fit(word_count, target_s=args.target_seconds, rate=rate))
        print(json.dumps(report, indent=2))
        return

    response = json.loads(post_json(f"/v1/text-to-speech/{args.voice}/with-timestamps", payload))
    audio_path = next_take(args.out_dir, args.name, ".mp3")
    audio_path.write_bytes(base64.b64decode(response["audio_base64"]))
    alignment = response.get("alignment") or response["normalized_alignment"]
    words = words_from_alignment(
        alignment["characters"], alignment["character_start_times_seconds"], alignment["character_end_times_seconds"]
    )
    words_path = audio_path.with_suffix(".words.json")
    words_path.write_text(json.dumps([asdict(w) for w in words], indent=1) + "\n")
    write_sidecar(audio_path, tool="narrate", request={"voice_id": args.voice, **payload}, credits_estimate=credits)
    level = take_level(audio_path, quiet_below=QUIET_TAKE_LUFS)
    print(json.dumps({
        "audio": str(audio_path),
        "words": str(words_path),
        "word_count": len(words),
        "speech_end_s": words[-1].end if words else 0.0,
        "credits_estimate": credits,
        "integrated_lufs": level.integrated_lufs,
        "true_peak_dbtp": level.true_peak_dbtp,
        "warnings": level.warnings,
    }, indent=2))


if __name__ == "__main__":
    main()
