"""Save a narration take made with the ElevenLabs MCP into the project, with word timings.

The MCP route needs no API key. In the conversation:
  1. creative_generate_speech with generations_count=1 (the default is 2 takes, billed twice).
  2. creative_transcribe_audio on the same flow with connect_from=[that speech node].
     Linked to the speech node it costs 0 credits and times the exact script text.
     A re-uploaded copy of the audio is transcribed blind instead: it is billed per
     second and gets names wrong ("Lumio" -> "Lumeo"), so wordStart() stops matching.
  3. creative_get_flow_run_status for both runs: the take's audio `url` and the
     transcript's `words_download_url`.
Run this within about 2 hours of generating; the signed links expire.

Writes, never overwriting earlier takes:
  <out-dir>/<name>_vN.mp3         the narration
  <out-dir>/<name>_vN.words.json  [{"text", "start", "end"}] in seconds, for cueing animation
  <out-dir>/<name>_vN.gen.json    what was asked for, so the take can be redone
Prints the take's loudness and true peak, with a warning when it is quiet: music and
effect levels are set against it.

Usage: import_mcp_narration.py --audio-url URL --words-url URL [--name narration]
                               [--voice ID] [--model ID] [--text TEXT | --script FILE]
                               [--out-dir public/assets/narration]
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict
from pathlib import Path

from elevenlabs_api import next_take, write_sidecar
from media import QUIET_TAKE_LUFS, take_level
from narrate import Word


def words_from_transcript(transcript: object) -> list[Word]:
    """Convert an MCP transcript (``{"words": [...]}`` or the bare list) into the skill's word list.

    Punctuation-only tokens such as an em dash come back as timed "words"; they are
    dropped because no animation can be cued from them.

    Raises:
        ValueError: If the transcript does not hold a list of word objects.
    """
    entries = transcript.get("words") if isinstance(transcript, dict) else transcript
    if not isinstance(entries, list) or not all(isinstance(entry, dict) for entry in entries):
        raise ValueError("transcript must be a list of word objects or {'words': [...]}")
    return [
        Word(str(entry["text"]), float(entry["start"]), float(entry["end"]))
        for entry in entries
        if entry.get("type", "word") == "word" and any(char.isalnum() for char in str(entry["text"]))
    ]


def download(url: str, what: str) -> bytes:
    """Fetch a signed MCP link; errors name the link without its signature."""
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https":
        sys.exit(f"{what} link must be https, got {parsed.scheme or 'no scheme'}")
    try:
        with urllib.request.urlopen(url, timeout=120) as response:
            return response.read()
    except urllib.error.HTTPError as err:
        hint = " (links expire about 2 hours after generation; read fresh ones with creative_get_flow_run_status)"
        sys.exit(f"Downloading the {what} from {parsed.netloc}{parsed.path} failed with HTTP {err.code}{hint}")
    except urllib.error.URLError as err:
        sys.exit(f"Downloading the {what} from {parsed.netloc}{parsed.path} failed: {err.reason}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--audio-url", required=True, help="the take's `url` from creative_get_flow_run_status")
    parser.add_argument("--words-url", required=True, help="the linked transcript's `words_download_url`")
    parser.add_argument("--name", default="narration")
    parser.add_argument("--voice", help="voice_id used, recorded in .gen.json")
    parser.add_argument("--model", help="model_id used, recorded in .gen.json")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--text", help="the narrated text, recorded in .gen.json")
    source.add_argument("--script", type=Path, help="text file holding the narrated text")
    parser.add_argument("--out-dir", type=Path, default=Path("public/assets/narration"))
    args = parser.parse_args()

    text = args.script.read_text().strip() if args.script else args.text
    words = words_from_transcript(json.loads(download(args.words_url, "word timings")))
    if not words:
        sys.exit("The transcript has no words; was creative_transcribe_audio linked to the speech node?")
    audio = download(args.audio_url, "audio")

    audio_path = next_take(args.out_dir, args.name, ".mp3")
    audio_path.write_bytes(audio)
    words_path = audio_path.with_suffix(".words.json")
    words_path.write_text(json.dumps([asdict(w) for w in words], indent=1) + "\n")
    request = {"source": "elevenlabs-mcp", "voice_id": args.voice, "model_id": args.model, "text": text}
    write_sidecar(
        audio_path,
        tool="import_mcp_narration",
        request={k: v for k, v in request.items() if v is not None},
        credits_estimate=float(len(text)) if text else None,
    )
    level = take_level(audio_path, quiet_below=QUIET_TAKE_LUFS)
    print(json.dumps({
        "audio": str(audio_path),
        "words": str(words_path),
        "word_count": len(words),
        "last_word_end_s": words[-1].end,
        "integrated_lufs": level.integrated_lufs,
        "true_peak_dbtp": level.true_peak_dbtp,
        "warnings": level.warnings,
    }, indent=2))


if __name__ == "__main__":
    main()
