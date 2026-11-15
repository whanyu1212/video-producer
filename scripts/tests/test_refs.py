"""references/library.json stays well formed, and refs.py lists, shows and starts studying entries."""

import json
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

LIBRARY = Path(__file__).resolve().parents[2] / "references" / "library.json"


@pytest.fixture(scope="module")
def library() -> dict[str, Any]:
    return json.loads(LIBRARY.read_text())


def test_library_ids_are_stable_and_unique(library: dict[str, Any]) -> None:
    """IDs are quoted by the user across projects: one per entry, numbered within its genre."""
    ids = [e["id"] for e in library["entries"]]
    assert len(ids) == len(set(ids))
    genre_ids = {g["id"] for g in library["genres"]}
    for entry in library["entries"]:
        genre, number = entry["id"].split("-")
        assert genre == entry["genre"] and genre in genre_ids
        assert re.fullmatch(r"\d{2}", number)


def test_library_fields_are_valid(library: dict[str, Any]) -> None:
    for entry in library["entries"]:
        assert entry["make_with"] in library["make_with"], entry["id"]
        assert entry["verified"] in {"fetched", "search"}, entry["id"]
        assert entry["url"].startswith("https://"), entry["id"]


@pytest.fixture
def refs(tmp_path: Path, run_script: Callable[..., dict[str, Any]]) -> Callable[..., dict[str, Any]]:
    return lambda *args: run_script("refs.py", "--root", str(tmp_path / "refs"), *args)


def test_genres_overview_counts_entries(refs: Callable[..., dict[str, Any]], library: dict[str, Any]) -> None:
    overview = refs("genres")["genres"]
    assert sum(g["entries"] for g in overview) == len(library["entries"])


def test_list_filters_by_genre_and_make(refs: Callable[..., dict[str, Any]]) -> None:
    listed = refs("list", "--genre", "D1", "--make", "code")["entries"]
    assert listed and all(e["id"].startswith("D1-") and e["make_with"] == "code" for e in listed)
    assert set(listed[0]) == {"id", "make_with", "title", "maker", "studied"}


def test_show_unknown_id_is_refused(refs: Callable[..., dict[str, Any]]) -> None:
    with pytest.raises(RuntimeError):
        refs("show", "Z9-99")


def test_study_starts_notes_once(refs: Callable[..., dict[str, Any]]) -> None:
    started = refs("study", "E1-01")
    notes = Path(started["notes"])
    assert notes.read_text().startswith("# E1-01")
    assert refs("show", "E1-01")["entries"][0]["studied"] is True
    with pytest.raises(RuntimeError):  # never overwrites notes already written
        refs("study", "E1-01")


def test_house_style_is_created_once(refs: Callable[..., dict[str, Any]]) -> None:
    path = Path(refs("house")["house_style"])
    path.write_text(path.read_text() + "\n- kept this line\n")
    assert "kept this line" in Path(refs("house")["house_style"]).read_text()
