"""Shared fixtures: running a script as the user would, and making small media files with ffmpeg."""

import json
import runpy
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

SCRIPTS = Path(__file__).resolve().parents[1]


@pytest.fixture
def run_script(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> Callable[..., dict[str, Any]]:
    """Run ``scripts/<name>`` with arguments and parse the JSON it prints.

    The script runs in this process as ``__main__`` (not a subprocess), so coverage
    tools see its lines. A non-zero exit raises, as a failed command would.
    """

    def run(name: str, *args: str) -> dict[str, object]:
        monkeypatch.setattr(sys, "argv", [str(SCRIPTS / name), *args])
        capsys.readouterr()
        try:
            runpy.run_path(str(SCRIPTS / name), run_name="__main__")
        except SystemExit as exit_:
            if exit_.code not in (0, None):
                raise RuntimeError(f"{name} exited with {exit_.code!r}") from exit_
        return json.loads(capsys.readouterr().out)

    return run


@pytest.fixture
def lavfi(tmp_path: Path) -> Callable[[str, str], Path]:
    """Render an ffmpeg lavfi source into ``tmp_path``; skips the test without ffmpeg."""
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg not installed")

    def make(source: str, name: str) -> Path:
        path = tmp_path / name
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", source, "-frames:v", "1", str(path)]
            if path.suffix in {".png", ".jpg"}
            else ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", source, str(path)],
            check=True,
        )
        return path

    return make
