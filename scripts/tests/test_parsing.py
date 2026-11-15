"""Tests for the scripts' pure parsing logic (see pyproject.toml for how to run)."""

import pytest
from compose_music import plan_problems
from import_mcp_narration import words_from_transcript
from loudnorm_export import parse_loudnorm_json
from media import Loudness, parse_ebur128_summary, parse_spans
from narrate import Word, words_from_alignment


def test_alignment_collapses_to_words() -> None:
    text = " Hi  there.\n"
    starts = [0.0, 0.1, 0.2, 0.3, 0.35, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    ends = [s + 0.05 for s in starts]
    assert words_from_alignment(list(text), starts, ends) == [
        Word("Hi", starts[1], ends[2]),
        Word("there.", starts[5], ends[10]),
    ]


def test_alignment_rejects_mismatched_lengths() -> None:
    with pytest.raises(ValueError):
        words_from_alignment(["a", "b"], [0.0], [0.1])


MCP_WORDS = [
    {"text": "docs.sylph.ai", "type": "word", "start": 11.854, "end": 13.084},
    {"text": "—", "type": "word", "start": 13.166, "end": 13.746},
    {"text": " ", "type": "spacing", "start": 13.746, "end": 13.839},
    {"text": "don't;", "type": "word", "start": 14.06, "end": 14.443},
]


@pytest.mark.parametrize("transcript", [{"words": MCP_WORDS}, MCP_WORDS], ids=["download", "bare-list"])
def test_mcp_transcript_keeps_spoken_words(transcript: object) -> None:
    assert words_from_transcript(transcript) == [Word("docs.sylph.ai", 11.854, 13.084), Word("don't;", 14.06, 14.443)]


@pytest.mark.parametrize("transcript", [{"text": "no words"}, ["not a word object"]], ids=["no-words", "bad-entry"])
def test_mcp_transcript_rejects_other_shapes(transcript: object) -> None:
    with pytest.raises(ValueError):
        words_from_transcript(transcript)


EBUR128_TAIL = """
[Parsed_ebur128_0 @ 0x1] Summary:

  Integrated loudness:
    I:         -14.1 LUFS
    Threshold: -24.4 LUFS

  Loudness range:
    LRA:         5.2 LU
    Threshold: -34.5 LUFS

  True peak:
    Peak:       -1.3 dBFS
"""


def test_ebur128_summary() -> None:
    assert parse_ebur128_summary("t: 9.9 M: -12 S: -13\n" + EBUR128_TAIL) == Loudness(-14.1, -1.3, 5.2)


def test_ebur128_without_summary() -> None:
    assert parse_ebur128_summary("no audio here") is None


def test_detect_spans_pair_markers() -> None:
    log = "lavfi.freezedetect.freeze_start: 2\nlavfi.freezedetect.freeze_end: 3.5\nblack_start:0 black_end:0.4 black_duration:0.4"
    assert parse_spans(log, "freeze_start", "freeze_end") == [(2.0, 3.5)]
    assert parse_spans(log, "black_start", "black_end") == [(0.0, 0.4)]


def test_loudnorm_measurement_is_last_json_block() -> None:
    stderr = 'noise {"x": 1}\n[Parsed_loudnorm_0 @ 0x1]\n{\n "input_i" : "-25.36", "input_tp" : "-20.00", "input_lra" : "3.2", "input_thresh" : "-35.6", "target_offset" : "0.3"\n}\n'
    assert parse_loudnorm_json(stderr)["input_i"] == "-25.36"


@pytest.mark.parametrize(
    ("chunks", "problem"),
    [
        ([], "non-empty"),
        ([{"text": "[Intro]", "duration_ms": 2000, "positive_styles": ["piano"]}], "duration_ms"),
        ([{"text": "[Intro]", "duration_ms": 4000, "positive_styles": []}], "positive_styles"),
        ([{"text": "x" * 201, "duration_ms": 4000, "positive_styles": ["piano"]}], "200 characters"),
    ],
    ids=["empty", "too-short", "no-styles", "long-line"],
)
def test_plan_problems(chunks: list[dict[str, object]], problem: str) -> None:
    assert any(problem in message for message in plan_problems({"chunks": chunks}))


def test_valid_plan_has_no_problems() -> None:
    plan = {"chunks": [{"text": "[Intro]", "duration_ms": 4000, "positive_styles": ["piano"], "negative_styles": ["vocals"]}]}
    assert plan_problems(plan) == []
