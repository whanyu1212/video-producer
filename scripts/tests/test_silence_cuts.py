from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from narrate import Word
from silence_cuts import Cut, nearest_cut, parse_word_ref, place_cuts, quiet_spans, rms_levels, word_ends


def test_rms_levels_of_full_scale_square_and_silence() -> None:
    rate = 1000
    square = [32767, -32767] * (rate // 2)
    levels = rms_levels([*square, *[0] * rate], rate, window_s=0.05, hop_s=0.1)
    assert levels[:5] == pytest.approx([0.0] * 5, abs=0.01)
    assert all(level < -100 for level in levels[-5:])


def test_rms_levels_window_is_centred_and_narrow() -> None:
    rate = 1000
    levels = rms_levels([*[32767, -32767] * 250, *[0] * 500], rate, window_s=0.05, hop_s=0.01)
    assert levels[47] == pytest.approx(0.0, abs=0.01)  # the 50 ms window is all tone
    assert levels[50] == pytest.approx(-3.0, abs=0.1)  # half tone, half silence
    assert levels[53] < -100  # all silence


def test_rms_levels_of_quiet_tone() -> None:
    # A square wave at 1/1000 of full scale sits at -60 dBFS.
    levels = rms_levels([33, -33] * 500, 1000)
    assert levels == pytest.approx([-60.0] * len(levels), abs=0.1)


@pytest.mark.parametrize(
    ("levels", "spans"),
    [
        ([-20, -70, -70, -70, -20, -61, -20], [(0.1, 0.4)]),
        ([-20, -70, -20, -70, -70, -70, -70], [(0.3, 0.7)]),
        ([-70, -70, -70, -20], [(0.0, 0.3)]),
        ([-20, -59, -59, -59, -20], []),
        ([-20, -60, -60, -20], [(0.1, 0.3)]),
    ],
    ids=["middle", "short-gap-skipped-and-open-end", "from-start", "above-threshold", "at-threshold-and-min-length"],
)
def test_quiet_spans(levels: list[float], spans: list[tuple[float, float]]) -> None:
    assert quiet_spans(levels, -60, min_len_s=0.2, hop_s=0.1) == spans


SPANS = [(11.89, 12.14), (23.48, 23.76)]


@pytest.mark.parametrize(
    ("near", "cut"),
    [
        (11.99, Cut(11.99, 12.015, (11.89, 12.14), 0.025)),
        (11.62, Cut(11.62, 12.015, (11.89, 12.14), 0.395)),
        (20.0, Cut(20.0, 23.62, (23.48, 23.76), 3.62)),
    ],
    ids=["inside", "word-end-before", "picks-nearer"],
)
def test_nearest_cut(near: float, cut: Cut) -> None:
    assert nearest_cut(SPANS, near) == cut


@pytest.mark.parametrize(
    ("spans", "near"),
    [([(12.3, 13.0), (10.0, 12.0)], 11.9), ([(9.0, 9.95), (10.0, 12.0)], 10.1)],
    ids=["near-its-end", "near-its-start"],
)
def test_nearest_cut_prefers_the_silence_it_is_in(spans: list[tuple[float, float]], near: float) -> None:
    cut = nearest_cut(spans, near)
    assert cut is not None and cut.silence_s == (10.0, 12.0)


def test_nearest_cut_without_silence() -> None:
    assert nearest_cut([], 3.0) is None


@pytest.mark.parametrize(
    ("ref", "parsed"),
    [("G.A.D.", ("G.A.D.", 0)), ("When:1", ("When", 1)), ("ratio:x", ("ratio:x", 0))],
)
def test_parse_word_ref(ref: str, parsed: tuple[str, int]) -> None:
    assert parse_word_ref(ref) == parsed


TAKE = [Word("fine?", 5.1, 5.3), Word("When", 6.06, 6.2), Word("most", 6.5, 6.7), Word("most", 9.0, 9.2)]


def test_word_ends_resolve_nth_and_report_missing_words() -> None:
    assert word_ends(TAKE, ["fine?", "most:1", "most:2", "pricing"]) == (
        [("fine?", 5.3), ("most:1", 9.2)],
        ["'most' occurrence 2 is not in the take (2 found)", "'pricing' occurrence 0 is not in the take (0 found)"],
    )


def test_place_cuts_sorts_labels_and_warns_when_far() -> None:
    cuts, warnings = place_cuts(SPANS, [(None, 23.6), ("G.A.D.", 11.62), (None, 18.0)], max_off=0.5)
    assert [cut["cut_s"] for cut in cuts] == [12.015, 23.62, 23.62]
    assert cuts[0]["after"] == "G.A.D." and "after" not in cuts[2]
    assert warnings == ["nearest silence to 18.0s is 5.62s away (cut at 23.62s): check the time"]


def test_place_cuts_allows_exactly_max_off() -> None:
    assert place_cuts([(11.0, 12.0)], [(None, 11.0)], max_off=0.5)[1] == []


def test_place_cuts_without_silence() -> None:
    assert place_cuts([], [(None, 3.0)], max_off=0.5) == ([], ["no silence in the take at this threshold: nothing to cut at 3.0s"])


def test_cuts_land_in_a_measured_gap(
    lavfi: Callable[[str, str], Path], run_script: Callable[..., dict[str, Any]]
) -> None:
    # Tone, 0.4 s of silence from 1.0 s, tone, then 0.5 s of silence to the end.
    take = lavfi("aevalsrc='if(between(t,1,1.4)+gte(t,2.4),0,0.3*sin(2*PI*440*t))':s=44100:d=2.9", "take.wav")
    report = run_script("silence_cuts.py", str(take), "--at", "0.9", "--at", "1.8")
    assert report["speech_end_s"] == pytest.approx(2.4, abs=0.04)
    cut = report["cuts"][0]
    assert cut["cut_s"] == pytest.approx(1.2, abs=0.02)
    assert cut["silence_s"][0] == pytest.approx(1.0, abs=0.04)
    assert cut["silence_s"][1] == pytest.approx(1.4, abs=0.04)
    assert len(report["warnings"]) == 1
    assert report["warnings"][0].startswith("nearest silence to 1.8s is -0.5")


def take_with_floor(noise_amplitude: float) -> str:
    """A 4 s tone with a 1 s gap in the middle, over white noise of the given amplitude (0.002 ≈ -59 dBFS RMS)."""
    return (
        "sine=f=300:d=4:r=16000,volume='if(between(t,1.5,2.5),0,0.5)':eval=frame[a];"
        f"anoisesrc=d=4:c=white:a={noise_amplitude}:r=16000[b];[a][b]amix=inputs=2:normalize=0"
    )


@pytest.mark.parametrize(("noise", "warns"), [(0.002, True), (0.00002, False)], ids=["noisy-take", "clean-take"])
def test_noise_floor_near_threshold_suggests_one(
    lavfi: Callable[[str, str], Path], run_script: Callable[..., dict[str, Any]], noise: float, warns: bool
) -> None:
    """A take whose quiet parts sit near -60 has no silence at -60: say so, with a threshold that works."""
    report = run_script("silence_cuts.py", str(lavfi(take_with_floor(noise), "take.wav")), "--at", "2.0")
    floor_warnings = [w for w in report["warnings"] if "noise floor" in w]
    assert bool(floor_warnings) is warns
    if warns:
        assert report["noise_floor_db"] > -62
        suggested = float(floor_warnings[0].split("retry with --threshold ")[1].split()[0])
        retry = run_script("silence_cuts.py", str(lavfi(take_with_floor(noise), "retry.wav")), "--at", "2.0", "--threshold", str(suggested))
        assert retry["cuts"][0]["cut_s"] == pytest.approx(2.0, abs=0.1)
