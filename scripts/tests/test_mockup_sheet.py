from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from media import ffprobe
from mockup_sheet import GAP, Item, grid_size, parse_item, render_html, tile_filter


@pytest.mark.parametrize(
    ("arg", "expected"),
    [
        ("out/mockup_A.png=A · Soft & grounded", Item(Path("out/mockup_A.png"), "A · Soft & grounded")),
        ("out/mockup_B.png", Item(Path("out/mockup_B.png"), "mockup_B")),
        ("out/mockup_C.png=", Item(Path("out/mockup_C.png"), "mockup_C")),
    ],
    ids=["label", "no-label", "empty-label"],
)
def test_parse_item(arg: str, expected: Item) -> None:
    assert parse_item(arg) == expected


@pytest.mark.parametrize(
    ("count", "cols", "grid"),
    [(4, 2, (2, 2)), (3, 2, (2, 2)), (2, 3, (2, 1)), (5, 3, (3, 2)), (1, 2, (1, 1))],
)
def test_grid_size(count: int, cols: int, grid: tuple[int, int]) -> None:
    assert grid_size(count, cols) == grid


def test_tile_filter_places_cells_row_by_row() -> None:
    graph = tile_filter(3, 2, 100, 50)
    assert f"layout=0_0|{100 + GAP}_0|0_{50 + GAP}" in graph
    assert graph.count("force_original_aspect_ratio=decrease") == 3


def test_tile_filter_single_image_skips_xstack() -> None:
    graph = tile_filter(1, 2, 100, 50)
    assert "xstack" not in graph
    assert graph.endswith("[out]")


def test_html_escapes_labels_and_lists_audio() -> None:
    page = render_html(
        "Voices & looks",
        "",
        [Item(Path("a.png"), "A <soft>", "thin line")],
        [Item(Path("voice_a.mp3"), "Voice A")],
        uri=lambda path: f"inline:{path.name}",
    )
    assert "<title>Voices &amp; looks</title>" in page
    assert "<strong>A &lt;soft&gt;</strong> thin line" in page
    assert 'src="inline:a.png"' in page
    assert '<audio controls preload="auto" src="inline:voice_a.mp3">' in page


def test_html_without_audio_has_no_listen_section() -> None:
    page = render_html("Looks", "Pick one", [Item(Path("a.png"), "A")], [], uri=str)
    assert "<h2>Listen</h2>" not in page
    assert '<p class="intro">Pick one</p>' in page


def test_sheet_fits_mixed_shapes_into_equal_cells(
    lavfi: Callable[[str, str], Path], run_script: Callable[..., dict[str, Any]], tmp_path: Path
) -> None:
    wide = lavfi("color=c=red:s=320x180", "wide.png")
    tall = lavfi("color=c=blue:s=180x320", "tall.png")
    report = run_script(
        "mockup_sheet.py", f"{wide}=A · wide", f"{tall}=B · tall",
        "--cell-width", "160", "--out", str(tmp_path / "sheet"),
    )
    sheet = ffprobe(Path(str(report["png"])))["streams"][0]
    assert (sheet["width"], sheet["height"]) == (2 * (160 + GAP) + GAP, 90 + 2 * GAP)
    assert report["cells"] == [
        {"row": 1, "col": 1, "label": "A · wide", "image": str(wide)},
        {"row": 1, "col": 2, "label": "B · tall", "image": str(tall)},
    ]
    assert "A · wide" in (tmp_path / "sheet.html").read_text()

