"""Transcribe audio or video with ElevenLabs Scribe and save word timings.

For speech you did not generate (an interview, a screen recording's voice-over):
narrate.py already returns timings for its own takes. Billed by audio length;
check your plan's speech-to-text rate before long files.

Writes <out-dir>/<stem>.words.json ([{"text", "start", "end"}], seconds) and
<stem>.transcript.json (the full response). Refuses to overwrite.

Usage: transcribe.py FILE [--language en] [--diarize] [--out-dir DIR]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from elevenlabs_api import post_multipart


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("file", type=Path)
    parser.add_argument("--language", help="ISO-639 code; omitted means auto-detect")
    parser.add_argument("--diarize", action="store_true", help="label speakers")
    parser.add_argument("--model", default="scribe_v2")
    parser.add_argument("--out-dir", type=Path, help="default: next to FILE")
    args = parser.parse_args()

    out_dir = args.out_dir or args.file.parent
    words_path = out_dir / f"{args.file.stem}.words.json"
    transcript_path = out_dir / f"{args.file.stem}.transcript.json"
    if words_path.exists() or transcript_path.exists():
        sys.exit(f"{words_path} or {transcript_path} exists; move it first")

    fields = {"model_id": args.model, "timestamps_granularity": "word", "diarize": str(args.diarize).lower()}
    if args.language:
        fields["language_code"] = args.language
    response = json.loads(post_multipart("/v1/speech-to-text", fields, file_field="file", file_path=args.file))
    words = [
        {"text": w["text"], "start": w["start"], "end": w["end"], **({"speaker": w["speaker_id"]} if w.get("speaker_id") else {})}
        for w in response.get("words", [])
        if w.get("type") == "word"
    ]
    out_dir.mkdir(parents=True, exist_ok=True)
    words_path.write_text(json.dumps(words, indent=1) + "\n")
    transcript_path.write_text(json.dumps(response, indent=1) + "\n")
    print(json.dumps({
        "words": str(words_path),
        "transcript": str(transcript_path),
        "language": response.get("language_code"),
        "word_count": len(words),
    }, indent=2))


if __name__ == "__main__":
    main()
