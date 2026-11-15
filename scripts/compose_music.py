"""Compose music with ElevenLabs, either from a sectioned plan or a single prompt.

A plan pins each section's length so the music changes exactly where the video
does. Plan file (JSON) for model music_v2:
  {"chunks": [
     {"text": "[Intro]", "duration_ms": 4000,
      "positive_styles": ["warm felt piano", "slow build"], "negative_styles": ["vocals"]},
     ...]}
For an instrumental bed, put only the section name in "text" and add "vocals"
to negative_styles. Each chunk is 3,000-120,000 ms.

Costs about 900 credits per minute. --dry-run prints the estimate only.

Usage: compose_music.py (--plan PLAN.json | --prompt TEXT --length-s SECONDS [--instrumental])
                        [--name music] [--model music_v2] [--seed N]
                        [--out-dir public/assets/music] [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from elevenlabs_api import next_take, post_json, write_sidecar

CREDITS_PER_MINUTE = 900
CHUNK_MS_RANGE = (3_000, 120_000)
MAX_LINES, MAX_LINE_CHARS = 30, 200


def plan_problems(plan: dict[str, object]) -> list[str]:
    """Check a composition plan against the API's documented limits."""
    chunks = plan.get("chunks")
    if not isinstance(chunks, list) or not chunks:
        return ["plan needs a non-empty 'chunks' list"]
    problems: list[str] = []
    low, high = CHUNK_MS_RANGE
    for index, chunk in enumerate(chunks):
        label = f"chunk {index}"
        duration = chunk.get("duration_ms")
        if not isinstance(duration, int) or not low <= duration <= high:
            problems.append(f"{label}: duration_ms must be an integer {low}-{high}, got {duration!r}")
        if not chunk.get("positive_styles"):
            problems.append(f"{label}: positive_styles is required")
        lines = str(chunk.get("text", "")).splitlines()
        if len(lines) > MAX_LINES or any(len(line) > MAX_LINE_CHARS for line in lines):
            problems.append(f"{label}: text allows {MAX_LINES} lines of {MAX_LINE_CHARS} characters")
    return problems


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--plan", type=Path)
    source.add_argument("--prompt")
    parser.add_argument("--length-s", type=float, help="length for --prompt, 3-600 s")
    parser.add_argument("--instrumental", action="store_true", help="with --prompt: guarantee no vocals")
    parser.add_argument("--name", default="music")
    parser.add_argument("--model", default="music_v2")
    parser.add_argument("--seed", type=int, help="only with --plan")
    parser.add_argument("--out-dir", type=Path, default=Path("public/assets/music"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.plan:
        plan = json.loads(args.plan.read_text())
        problems = plan_problems(plan)
        if problems:
            sys.exit("Plan rejected:\n  " + "\n  ".join(problems))
        payload: dict[str, object] = {"composition_plan": plan, "model_id": args.model}
        if args.seed is not None:
            payload["seed"] = args.seed
        length_ms = sum(chunk["duration_ms"] for chunk in plan["chunks"])
    else:
        if args.length_s is None:
            sys.exit("--prompt needs --length-s")
        length_ms = round(args.length_s * 1000)
        payload = {"prompt": args.prompt, "music_length_ms": length_ms,
                   "force_instrumental": args.instrumental, "model_id": args.model}
    credits = round(length_ms / 60_000 * CREDITS_PER_MINUTE)
    if args.dry_run:
        print(json.dumps({"length_s": length_ms / 1000, "credits_estimate": credits, "payload": payload}, indent=2))
        return

    audio = post_json("/v1/music", payload, query={"output_format": "mp3_44100_128"}, timeout=600)
    path = next_take(args.out_dir, args.name, ".mp3")
    path.write_bytes(audio)
    write_sidecar(path, tool="compose_music", request=payload, credits_estimate=credits)
    print(json.dumps({"audio": str(path), "length_s": length_ms / 1000, "credits_estimate": credits}, indent=2))


if __name__ == "__main__":
    main()
