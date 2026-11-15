"""Save a music bed made with the ElevenLabs MCP into the project, with a record of how it was made.

The MCP route needs no API key, but it takes one prompt and a total length (no timed
sections; compose_music.py does plans). In the conversation:
  1. creative_get_model_schema for the music node and model, to read the parameter
     names (Music v2.5: duration_seconds, lyrics_type, instrumental).
  2. creative_add_flow_node (node_type "music") with the prompt and model_parameters,
     e.g. {"duration_seconds": 30, "lyrics_type": "instrumental", "instrumental": true}.
  3. creative_run_flow_nodes with generations_count=1: the default for music is 4
     variations, billed 4 times.
  4. creative_get_flow_run_status with the run's session_ids: the take's `url`, and the
     credits charged.
Run this within about 2 hours of generating; the signed link expires.

Writes, never overwriting earlier takes:
  <out-dir>/<name>_vN.mp3       the music
  <out-dir>/<name>_vN.gen.json  the prompt and parameters, so the bed can be redone
Prints its length, loudness and true peak, with a warning when the length is off the
one asked for or the true peak is above 0 dBTP (a clipped bed).

Usage: import_mcp_music.py --audio-url URL --prompt TEXT [--duration SECONDS] [--model ID]
                           [--instrumental] [--credits N] [--name music] [--out-dir public/assets/music]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from elevenlabs_api import next_take, write_sidecar
from import_mcp_narration import download
from media import ffprobe, take_level

LENGTH_TOLERANCE_S = 0.5


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--audio-url", required=True, help="the take's `url` from creative_get_flow_run_status")
    parser.add_argument("--prompt", required=True, help="the prompt the music node ran with")
    parser.add_argument("--duration", type=float, help="duration_seconds asked for")
    parser.add_argument("--model", help="model_id used, e.g. eleven_music_v2_5")
    parser.add_argument("--instrumental", action="store_true", help="the node ran with lyrics_type instrumental")
    parser.add_argument("--credits", type=float, help="credits the run reported")
    parser.add_argument("--name", default="music")
    parser.add_argument("--out-dir", type=Path, default=Path("public/assets/music"))
    args = parser.parse_args()

    audio = download(args.audio_url, "music")
    path = next_take(args.out_dir, args.name, ".mp3")
    path.write_bytes(audio)
    request = {
        "source": "elevenlabs-mcp",
        "model_id": args.model,
        "prompt": args.prompt,
        "duration_seconds": args.duration,
        "instrumental": args.instrumental or None,
    }
    write_sidecar(path, tool="import_mcp_music", request={k: v for k, v in request.items() if v is not None}, credits_estimate=args.credits)

    length = float(ffprobe(path)["format"]["duration"])
    level = take_level(path, peak_ceiling=0.0)
    warnings = list(level.warnings)
    if args.duration is not None and abs(length - args.duration) > LENGTH_TOLERANCE_S:
        warnings.append(f"the bed is {length:.2f}s, {args.duration}s was asked for: re-fit it with atempo or trim and fade")
    print(json.dumps({
        "audio": str(path),
        "duration_s": round(length, 3),
        "integrated_lufs": level.integrated_lufs,
        "true_peak_dbtp": level.true_peak_dbtp,
        "warnings": warnings,
    }, indent=2))


if __name__ == "__main__":
    main()
