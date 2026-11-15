"""Check Remotion scene code for things that make renders differ between runs or drift with the frame rate.

Errors (exit 1), from SKILL.md's Remotion rules: renders must be identical every time.
  random      Math.random(); use random('seed') from remotion
  timer       setTimeout, setInterval, requestAnimationFrame
  clock       Date.now(), new Date(), performance.now()
  css-motion  CSS transition or animation values, @keyframes
Warnings:
  html-media  <video>, <audio> or <img>: use OffthreadVideo, Audio and Img from remotion,
              which hold the frame until the media has loaded
  frame-literal  motion timed in frame numbers (interpolate(frame, [30, 60]), frame > 120,
              frame - 45); time it in seconds (frame / fps) or from cue() so it holds at any fps

Comments are ignored (a // inside a string is not one). Rules match across line breaks,
so a call split over several lines is checked like one on a single line. Prop names are
not checked, only code that does the thing.

Usage: lint_scenes.py [PATH ...]   (default: src; folders are searched for .ts and .tsx files)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

RULES: list[tuple[str, str, re.Pattern[str], str]] = [
    ("random", "error", re.compile(r"\bMath\.random\s*\("), "Math.random() differs every render; use random('seed') from remotion"),
    ("timer", "error", re.compile(r"\b(?:setTimeout|setInterval|requestAnimationFrame)\s*\("),
     "timers run on the clock, not the frame; drive it from useCurrentFrame()"),
    ("clock", "error", re.compile(r"\bDate\.now\s*\(|\bnew\s+Date\s*\(\s*\)|\bperformance\.now\s*\("),
     "the wall clock differs every render; derive time from the frame"),
    ("css-motion", "error",
     re.compile(r"\b(?:transition|animation)\s*:\s*['\"`][^'\"`]*?(?:\d+m?s\b|\bease|\blinear\b|\binfinite\b)|@keyframes\b"),
     "CSS transitions and animations ignore the frame; interpolate from useCurrentFrame()"),
    ("html-media", "warning", re.compile(r"<(?:video|audio|img)\b"),
     "plain HTML media is not awaited, so frames can render before it loads; use OffthreadVideo, Audio or Img from remotion"),
    # Frame numbers scaled by the fps (`[0, 0.5 * fps]`, `30 * fps`, `sec(2)`) are fine.
    ("frame-literal", "warning",
     re.compile(r"\binterpolate\(\s*frame\s*,\s*\[(?![^\]]*(?:fps|FPS|sec\())\s*-?\d"
                r"|\bframe\s*(?:[<>]=?|===?|!==?|[-+])\s*\d{2,}\b(?!\s*\*\s*(?:fps|FPS))"),
     "timed in frame numbers, so it changes with the fps; use seconds (frame / fps) or cue()"),
]

QUOTES = "'\"`"


@dataclass(frozen=True)
class Finding:
    file: str
    line: int
    rule: str
    level: str
    message: str


def strip_comments(code: str) -> str:
    """Blank out // and /* */ comments outside string literals, keeping every newline.

    Strings stay as they are, so a URL's // does not hide the code after it. Code inside
    a template literal's ${...} is kept too; a comment there is rare and is left in.
    """
    out = list(code)
    i, quote = 0, ""
    while i < len(code):
        char = code[i]
        if quote:
            if char == "\\":
                i += 2
                continue
            if char == quote:
                quote = ""
        elif char in QUOTES:
            quote = char
        elif code.startswith("//", i):
            end = code.find("\n", i)
            end = len(code) if end == -1 else end
            out[i:end] = " " * (end - i)
            i = end
            continue
        elif code.startswith("/*", i):
            end = code.find("*/", i + 2)
            end = len(code) if end == -1 else end + 2
            out[i:end] = [c if c == "\n" else " " for c in code[i:end]]
            i = end
            continue
        i += 1
    return "".join(out)


def lint_source(code: str, path: Path) -> list[Finding]:
    """Every rule matched over the whole file; a finding is reported once per rule and line, at its first line."""
    text = strip_comments(code)
    found: dict[tuple[int, str], Finding] = {}
    for rule, level, pattern, message in RULES:
        for match in pattern.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            found.setdefault((line, rule), Finding(str(path), line, rule, level, message))
    return sorted(found.values(), key=lambda f: (f.line, f.rule))


def source_files(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_dir():
            files += sorted(p for p in path.rglob("*") if p.suffix in {".ts", ".tsx"} and "node_modules" not in p.parts)
        elif path.exists():
            files.append(path)
        else:
            sys.exit(f"{path} not found")
    return files


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("paths", nargs="*", type=Path, default=[Path("src")])
    args = parser.parse_args()
    files = source_files(args.paths)
    findings = [f for path in files for f in lint_source(path.read_text(), path)]
    errors = sum(f.level == "error" for f in findings)
    print(json.dumps({
        "checked": len(files),
        "errors": errors,
        "warnings": len(findings) - errors,
        "findings": [asdict(f) for f in findings],
    }, indent=2))
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
