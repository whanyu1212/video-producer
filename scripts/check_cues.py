"""Check animation cues against a narration take's word timings before rendering.

`wordStart(words, "when")` and `cue("when")` match words the way the template's
`src/lib/words.ts` does (lower case, letters, digits and apostrophes only) and
take the first occurrence unless given `nth`. A word spoken twice therefore cues
the first one, and the beat fires early. This script prints JSON with:
  repeated    every word spoken more than once: each occurrence's nth, start and context
  mismatches  where the take's words differ from the script (a respelled name
              such as "Lumio" -> "Lumeo" makes wordStart() throw), with --script
  cues        every cue("…", n) / wordStart(words, "…", n) call found under --src,
              resolved to its start time and context
  warnings    cues that name a missing word or occurrence, and repeated words cued
              without an explicit nth

Usage: check_cues.py WORDS_JSON [--script script.txt] [--src src]
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from narrate import Word

CONTEXT_WORDS = 3
CUE_CALL = re.compile(
    r"\b(?:cue|wordStart)\(\s*(?:[A-Za-z_$][\w$.]*\s*,\s*)?(['\"`])((?:(?!\1).)+)\1\s*(?:,\s*([^)]*?)\s*)?\)"
)


def normalize(text: str) -> str:
    """The key words.ts matches on: lower case, keeping letters, digits and ASCII apostrophes."""
    return "".join(char for char in text.lower() if char.isalnum() or char == "'")


def load_words(path: Path) -> list[Word]:
    return [Word(str(w["text"]), float(w["start"]), float(w["end"])) for w in json.loads(path.read_text())]


def occurrences(words: list[Word]) -> dict[str, list[int]]:
    """Indexes into ``words`` of each normalized word, in spoken order."""
    found: dict[str, list[int]] = defaultdict(list)
    for index, word in enumerate(words):
        key = normalize(word.text)
        if key:
            found[key].append(index)
    return found


def context(words: list[Word], index: int) -> str:
    """The word in brackets with a few words either side, as spoken."""
    before = [w.text for w in words[max(0, index - CONTEXT_WORDS):index]]
    after = [w.text for w in words[index + 1:index + 1 + CONTEXT_WORDS]]
    return " ".join([*before, f"[{words[index].text}]", *after])


def repeated_words(words: list[Word]) -> dict[str, list[dict[str, object]]]:
    return {
        key: [{"nth": nth, "start_s": words[i].start, "context": context(words, i)} for nth, i in enumerate(indexes)]
        for key, indexes in occurrences(words).items()
        if len(indexes) > 1
    }


def script_mismatches(script: str, words: list[Word]) -> list[dict[str, object]]:
    """Stretches where the take's words differ from the script's, compared as words.ts compares them."""
    expected = [token for token in script.split() if normalize(token)]
    spoken = [normalize(w.text) for w in words if normalize(w.text)]
    spoken_words = [w for w in words if normalize(w.text)]
    matcher = difflib.SequenceMatcher(a=[normalize(t) for t in expected], b=spoken, autojunk=False)
    return [
        {
            "script": " ".join(expected[a0:a1]),
            "take": " ".join(w.text for w in spoken_words[b0:b1]),
            "at_s": spoken_words[min(b0, len(spoken_words) - 1)].start if spoken_words else None,
        }
        for tag, a0, a1, b0, b1 in matcher.get_opcodes()
        if tag != "equal"
    ]


@dataclass(frozen=True)
class CueCall:
    file: str
    line: int
    word: str
    nth: str | None


def find_cue_calls(source: str, file: str) -> list[CueCall]:
    """Calls with a literal word; ``nth`` is kept as written (a number or an expression)."""
    return [
        CueCall(file, source.count("\n", 0, match.start()) + 1, match.group(2), match.group(3) or None)
        for match in CUE_CALL.finditer(source)
    ]


def check_call(call: CueCall, words: list[Word], found: dict[str, list[int]]) -> tuple[dict[str, object], str | None]:
    """Resolve one call; returns its report and a warning, if any."""
    where = f"{call.file}:{call.line}"
    indexes = found.get(normalize(call.word), [])
    report: dict[str, object] = {"at": where, "word": call.word, "nth": call.nth, "occurrences": len(indexes)}
    if call.nth is not None and not call.nth.isdigit():
        return report, None
    nth = int(call.nth or 0)
    if nth >= len(indexes):
        return report, f"{where}: '{call.word}' occurrence {nth} is not in the take ({len(indexes)} found); wordStart() will throw"
    report |= {"start_s": words[indexes[nth]].start, "context": context(words, indexes[nth])}
    if call.nth is None and len(indexes) > 1:
        return report, (
            f"{where}: '{call.word}' is spoken {len(indexes)} times and the cue takes the first "
            f"({context(words, indexes[0])}); pass nth if another was meant"
        )
    return report, None


def check_sources(files: list[Path], words: list[Word]) -> tuple[list[dict[str, object]], list[str]]:
    """Resolve every cue call in ``files``; returns the reports and the warnings."""
    found = occurrences(words)
    cues: list[dict[str, object]] = []
    warnings: list[str] = []
    for path in files:
        for call in find_cue_calls(path.read_text(), str(path)):
            cue, warning = check_call(call, words, found)
            cues.append(cue)
            if warning:
                warnings.append(warning)
    return cues, warnings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("words", type=Path, help="the take's .words.json")
    parser.add_argument("--script", type=Path, help="the narrated script, to find words the take spells differently")
    parser.add_argument("--src", type=Path, help="folder (or file) of .ts/.tsx to scan for cue()/wordStart() calls")
    args = parser.parse_args()

    words = load_words(args.words)
    report: dict[str, object] = {"words": len(words), "repeated": repeated_words(words)}
    warnings: list[str] = []
    if args.script:
        mismatches = script_mismatches(args.script.read_text(), words)
        report["mismatches"] = mismatches
        warnings += [f"script '{m['script']}' vs take '{m['take']}' at {m['at_s']}s" for m in mismatches]
    if args.src:
        files = [args.src] if args.src.is_file() else sorted([*args.src.rglob("*.ts"), *args.src.rglob("*.tsx")])
        cues, cue_warnings = check_sources(files, words)
        report["cues"] = cues
        warnings += cue_warnings
    report["warnings"] = warnings
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
