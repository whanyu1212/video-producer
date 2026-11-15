"""Generate a sound effect with ElevenLabs.

Costs about 200 credits per sound. Prefer a free library sound when one fits;
--dry-run prints the estimate only.

Usage: sfx.py --text "short airy whoosh, left to right" --name whoosh
              [--duration 0.5-30] [--loop] [--influence 0-1] [--model eleven_text_to_sound_v2]
              [--out-dir public/assets/sfx] [--dry-run]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from elevenlabs_api import next_take, post_json, write_sidecar

CREDITS_PER_SOUND = 200


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--text", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--duration", type=float, help="0.5-30 s; omitted lets the model choose")
    parser.add_argument("--loop", action="store_true")
    parser.add_argument("--influence", type=float, help="0-1, how literally to follow the text (default 0.3)")
    parser.add_argument("--model")
    parser.add_argument("--out-dir", type=Path, default=Path("public/assets/sfx"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    optional = {"duration_seconds": args.duration, "prompt_influence": args.influence, "model_id": args.model}
    payload: dict[str, object] = {"text": args.text, "loop": args.loop}
    payload |= {k: v for k, v in optional.items() if v is not None}
    if args.dry_run:
        print(json.dumps({"credits_estimate": CREDITS_PER_SOUND, "payload": payload}, indent=2))
        return

    audio = post_json("/v1/sound-generation", payload, query={"output_format": "mp3_44100_128"})
    path = next_take(args.out_dir, args.name, ".mp3")
    path.write_bytes(audio)
    write_sidecar(path, tool="sfx", request=payload, credits_estimate=CREDITS_PER_SOUND)
    print(json.dumps({"audio": str(path), "credits_estimate": CREDITS_PER_SOUND}, indent=2))


if __name__ == "__main__":
    main()
