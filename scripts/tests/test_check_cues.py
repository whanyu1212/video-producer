import json
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pytest
from check_cues import (
    CueCall,
    check_call,
    context,
    find_cue_calls,
    normalize,
    occurrences,
    repeated_words,
    script_mismatches,
)
from narrate import Word

# A take where "when" is spoken twice and the title beat cues the second.
OPENING = [
    Word(text, start, start + 0.2)
    for text, start in [
        ("can't", 2.03), ("find", 2.31), ("it...", 2.65), ("even", 3.80), ("when", 4.08),
        ("everything", 4.30), ("looks", 4.80), ("fine?", 5.10), ("When", 6.06), ("that", 6.30), ("happens", 6.50),
    ]
]


@pytest.mark.parametrize(
    ("text", "key"),
    [("U.S.A.", "usa"), ("side-by-side", "sidebyside"), ("won't", "won't"), ("ready.", "ready"),
     ("When", "when"), ("won’t", "wont"), ("—", "")],
    ids=["initials", "hyphens", "apostrophe", "full-stop", "capital", "curly-apostrophe", "dash"],
)
def test_normalize_matches_words_ts(text: str, key: str) -> None:
    assert normalize(text) == key


def test_repeated_words_list_every_occurrence_with_context() -> None:
    assert repeated_words(OPENING) == {
        "when": [
            {"nth": 0, "start_s": 4.08, "context": "find it... even [when] everything looks fine?"},
            {"nth": 1, "start_s": 6.06, "context": "everything looks fine? [When] that happens"},
        ]
    }


def test_script_matching_the_take_has_no_mismatches() -> None:
    assert script_mismatches("can't find it... even when everything looks fine? When that happens", OPENING) == []


def test_script_mismatches_show_respelled_words() -> None:
    take = [Word(text, i * 0.5, i * 0.5 + 0.4) for i, text in enumerate(["Lumeo", "shows", "side", "by", "side", "diffs"])]
    assert script_mismatches("Lumio shows side-by-side diffs —", take) == [
        {"script": "Lumio", "take": "Lumeo", "at_s": 0.0},
        {"script": "side-by-side", "take": "side by side", "at_s": 1.0},
    ]


def test_script_mismatch_at_the_end_points_at_the_last_word() -> None:
    assert script_mismatches("can't find it... even when everything looks fine? When that happens today", OPENING) == [
        {"script": "today", "take": "", "at_s": 6.5}
    ]


@pytest.mark.parametrize(
    ("index", "expected"),
    [(1, "can't [find] it... even when"), (10, "fine? When that [happens]")],
    ids=["near-start", "last-word"],
)
def test_context_stops_at_the_ends(index: int, expected: str) -> None:
    assert context(OPENING, index) == expected


def test_find_cue_calls_reads_word_and_nth() -> None:
    source = "const a = cue('When', 1);\nconst b = wordStart(words, \"fine?\");\nconst c = cue(`stop`, n);\nconst d = cue(text);\n"
    assert find_cue_calls(source, "timeline.ts") == [
        CueCall("timeline.ts", 1, "When", "1"),
        CueCall("timeline.ts", 2, "fine?", None),
        CueCall("timeline.ts", 3, "stop", "n"),
    ]


@pytest.mark.parametrize(
    ("call", "start", "warning"),
    [
        (CueCall("t.ts", 1, "When", "1"), 6.06, None),
        (CueCall("t.ts", 1, "when", None), 4.08, "spoken 2 times and the cue takes the first"),
        (CueCall("t.ts", 1, "When", "2"), None, "occurrence 2 is not in the take"),
        (CueCall("t.ts", 1, "pricing", None), None, "occurrence 0 is not in the take"),
        (CueCall("t.ts", 1, "fine?", None), 5.10, None),
        (CueCall("t.ts", 1, "when", "nth"), None, None),
    ],
    ids=["nth-given", "repeated-without-nth", "nth-too-high", "missing-word", "unique-word", "nth-expression"],
)
def test_check_call(call: CueCall, start: float | None, warning: str | None) -> None:
    report, message = check_call(call, OPENING, occurrences(OPENING))
    assert report.get("start_s") == start
    if warning is None:
        assert message is None
    else:
        assert message is not None and warning in message


def test_repeated_cue_warning_shows_the_occurrence_it_takes() -> None:
    _, message = check_call(CueCall("t.ts", 1, "When", None), OPENING, occurrences(OPENING))
    assert message is not None and "(find it... even [when] everything looks fine?)" in message


def test_report_from_files(tmp_path: Path, run_script: Callable[..., dict[str, Any]]) -> None:
    words = tmp_path / "narration_v2.words.json"
    words.write_text(json.dumps([asdict(w) for w in OPENING]))
    script = tmp_path / "script.txt"
    script.write_text("can't find it... even when everything looks fine? When that happens")
    src = tmp_path / "src"
    src.mkdir()
    (src / "timeline.ts").write_text("export const TITLE = cue('When', 1);\nexport const EARLY = cue('when');\n")
    report = run_script("check_cues.py", str(words), "--script", str(script), "--src", str(src))
    assert report["words"] == len(OPENING)
    assert list(report["repeated"]) == ["when"]
    assert report["mismatches"] == []
    assert [cue["start_s"] for cue in report["cues"]] == [6.06, 4.08]
    assert len(report["warnings"]) == 1
    assert report["warnings"][0].startswith(f"{src / 'timeline.ts'}:2: 'when' is spoken 2 times")
