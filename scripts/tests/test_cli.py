import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "script",
    ["mockup_sheet.py", "check_cues.py", "silence_cuts.py", "match_levels.py", "synth_sfx.py", "music_beats.py", "import_mcp_music.py",
     "cut_frames.py", "frame_diff.py", "level_take.py", "loudnorm_export.py", "probe.py", "lint_scenes.py", "refs.py", "narrate.py"],
)
def test_help_explains_usage(script: str) -> None:
    result = subprocess.run([sys.executable, str(SCRIPTS / script), "--help"], capture_output=True, text=True, check=True)
    assert "Usage:" in result.stdout
