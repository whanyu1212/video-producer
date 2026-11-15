"""Browse the reference library and keep what was learned from each reference.

The library (references/library.json in this skill) holds links and our own notes on
why each work is worth studying. What is captured from a reference (its frames, the
notes written after studying it) and the user's house style live outside the skill,
under --root, because frames of other people's work must not be committed.

  refs.py genres                         the 21 genres with entry counts (start here: it is short)
  refs.py list --genre D1 [--make code]  one line per entry: id, make_with, title, maker, studied
  refs.py show E2-01 [D5-04 ...]         full entries, plus their notes when studied
  refs.py study E2-01                    start <root>/E2-01/notes.md (never overwrites) and
                                         print how to make its frame sheet
  refs.py house                          the house-style file's path, created on first use

Usage: refs.py [--root ~/Movies/video-projects/_references] {genres,list,show,study,house} ...
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

LIBRARY = Path(__file__).resolve().parents[1] / "references" / "library.json"
DEFAULT_ROOT = Path.home() / "Movies" / "video-projects" / "_references"

NOTES_TEMPLATE = """# {id} · {title}
{maker} · {url}
Studied {today}. Frames: <sheet.png beside this file, with the source times; or "notes only">

Keep this under about 150 words: it is read again in every project that uses it.

## Look
<palette, type, how full the frame is, composition>

## Motion
<what moves, how many layers at what speeds, the easing feel, how one moment becomes the next>

## Pacing
<new events or cuts per 10 s, holds, how it opens and how it ends>

## Sound
<voice, music and effects, and where they meet the picture>

## Borrow
<the specific moves worth taking>

## Avoid
<what would not suit our work, or reads as dated>
"""

HOUSE_TEMPLATE = """# House style

What the user has picked and rejected, across projects, with their reasons. Read it at
the brief; add a line after every choice the user makes between options.

## Liked
<- 2026-01-01 · project · what they chose · why>

## Rejected
<- 2026-01-01 · project · what they turned down · why>

## Standing preferences
<palettes, type, pacing, voice and music the user keeps returning to>
"""


def load_library() -> dict[str, Any]:
    return json.loads(LIBRARY.read_text())


def notes_path(root: Path, entry_id: str) -> Path:
    return root / entry_id / "notes.md"


def find(library: dict[str, Any], ids: list[str]) -> list[dict[str, Any]]:
    by_id = {e["id"]: e for e in library["entries"]}
    unknown = [i for i in ids if i not in by_id]
    if unknown:
        sys.exit(f"not in the library: {', '.join(unknown)} (refs.py genres, then refs.py list --genre XX)")
    return [by_id[i] for i in ids]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="where frame sheets, notes and the house style live")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("genres")
    listing = commands.add_parser("list")
    listing.add_argument("--genre", help="a genre id such as D1")
    listing.add_argument("--group", help="a group letter: E, C, D or S")
    listing.add_argument("--make", choices=["code", "mixed", "footage", "generated"])
    show = commands.add_parser("show")
    show.add_argument("ids", nargs="+")
    study = commands.add_parser("study")
    study.add_argument("id")
    commands.add_parser("house")
    args = parser.parse_args()
    library = load_library()

    if args.command == "genres":
        counts: dict[str, int] = {}
        for entry in library["entries"]:
            counts[entry["genre"]] = counts.get(entry["genre"], 0) + 1
        result: dict[str, Any] = {"genres": [
            {"id": g["id"], "group": g["group"], "name": g["name"], "entries": counts.get(g["id"], 0)} for g in library["genres"]
        ]}
    elif args.command == "list":
        entries = [
            e for e in library["entries"]
            if (args.genre is None or e["genre"] == args.genre)
            and (args.group is None or e["genre"].startswith(args.group))
            and (args.make is None or e["make_with"] == args.make)
        ]
        result = {"entries": [
            {"id": e["id"], "make_with": e["make_with"], "title": e["title"], "maker": e["maker"],
             "studied": notes_path(args.root, e["id"]).exists()} for e in entries
        ]}
    elif args.command == "show":
        shown = []
        for entry in find(library, args.ids):
            notes = notes_path(args.root, entry["id"])
            sheet = notes.with_name("sheet.png")
            shown.append(entry | {
                "studied": notes.exists(),
                "notes": notes.read_text() if notes.exists() else None,
                "sheet": str(sheet) if sheet.exists() else None,
            })
        result = {"entries": shown}
    elif args.command == "study":
        (entry,) = find(library, [args.id])
        notes = notes_path(args.root, entry["id"])
        if notes.exists():
            sys.exit(f"{notes} exists: edit it instead of starting again")
        notes.parent.mkdir(parents=True, exist_ok=True)
        notes.write_text(NOTES_TEMPLATE.format(today=datetime.now().astimezone().date().isoformat(), **entry))
        folder = notes.parent
        result = {
            "notes": str(notes),
            "sheet": str(folder / "sheet.png"),
            "from_a_clip": f"contact_sheet.py CLIP --cols 3 --rows 2 --out-dir {folder}  (then rename the sheet to sheet.png)",
            "from_chosen_frames": (f"extract_frame.py CLIP T1 T2 ... --out-dir {folder / 'frames'}, then "
                                   f"mockup_sheet.py FRAME.png=\"0:04\" ... --cols 3 --out {folder / 'sheet'}"),
            "without_a_clip": "write the notes from watching it; leave the sheet out",
        }
    else:
        house = args.root / "house-style.md"
        if not house.exists():
            house.parent.mkdir(parents=True, exist_ok=True)
            house.write_text(HOUSE_TEMPLATE)
        result = {"house_style": str(house)}
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
