"""lint_scenes.py: code that makes renders differ between runs, or ties motion to one frame rate."""

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from lint_scenes import lint_source

TEMPLATE_SRC = Path(__file__).resolve().parents[2] / "template" / "src"


def rules(code: str) -> list[str]:
    return [f.rule for f in lint_source(code, Path("Scene.tsx"))]


@pytest.mark.parametrize(
    ("code", "rule"),
    [
        ("const x = Math.random() * 10;", "random"),
        ("setTimeout(() => setShown(true), 300);", "timer"),
        ("const id = requestAnimationFrame(tick);", "timer"),
        ("const t = Date.now() / 1000;", "clock"),
        ("const start = performance.now();", "clock"),
        ("<div style={{transition: 'opacity 300ms ease'}} />", "css-motion"),
        ("<div style={{animation: 'spin 2s linear infinite'}} />", "css-motion"),
        ("const css = `@keyframes pulse { from { opacity: 0 } }`;", "css-motion"),
        ("<video src={src} autoPlay />", "html-media"),
        ("<img src={staticFile('logo.png')} />", "html-media"),
        ("const o = interpolate(frame, [30, 60], [0, 1]);", "frame-literal"),
        ("if (frame > 120) return null;", "frame-literal"),
        ("spring({frame: frame - 45, fps});", "frame-literal"),
    ],
)
def test_flags(code: str, rule: str) -> None:
    assert rules(code) == [rule]


@pytest.mark.parametrize(
    "code",
    [
        "const x = random('dots-' + i);",  # Remotion's seeded random
        "const o = interpolate(frame / fps, [0.3, 0.9], [0, 1]);",
        "spring({frame: frame - Math.round(0.15 * fps), fps});",
        "if (frame === 0) return null;",
        "const o = interpolate(frame, [0, 0.5 * fps], [0, 1]);",  # Remotion's usual idiom, scaled by fps
        "if (frame > 30 * fps) return null;",
        "spring({frame: frame - 10 * fps, fps});",
        "const o = interpolate(frame, [sec(1), sec(2)], [0, 1]);",
        "<Img src={staticFile('logo.png')} />",
        "<OffthreadVideo src={staticFile('clip.mp4')} />",
        "const beats = [{at: 3, transition: 'cut'}];",  # a data field, not CSS
        "<Header start={0} endAt={12} />",  # prop names alone are fine
        "// Math.random() is banned here; use random('seed')",
        "/* setTimeout would break the render */ const a = 1;",
    ],
)
def test_allows(code: str) -> None:
    assert rules(code) == []


@pytest.mark.parametrize(
    ("code", "rule"),
    [
        ('const image = "https://example.com/" + Math.random();', "random"),
        ("const a = 'a // b'; setTimeout(go, 10);", "timer"),
        ("const u = `http://x/${id}`; const t = Date.now();", "clock"),
        ("const o = interpolate(\n  frame,\n  [30, 60],\n  [0, 1],\n);", "frame-literal"),
        ("<div style={{\n  transition:\n    'opacity 300ms ease',\n}} />", "css-motion"),
    ],
    ids=["url-then-random", "slashes-in-string", "url-in-template", "multiline-interpolate", "multiline-transition"],
)
def test_strings_and_line_breaks_hide_nothing(code: str, rule: str) -> None:
    """A // inside a string is not a comment, and a call split over lines is still one call."""
    assert rules(code) == [rule]


def test_multiline_finding_reports_its_first_line() -> None:
    (finding,) = lint_source("const a = 1;\nconst o = interpolate(\n  frame,\n  [30, 60], [0, 1]);\n", Path("Scene.tsx"))
    assert finding.line == 2


def test_reports_line_numbers() -> None:
    (finding,) = lint_source("const a = 1;\n// note\nconst b = Math.random();\n", Path("Scene.tsx"))
    assert finding.line == 3


def test_template_is_clean() -> None:
    """The template is what new projects start from: it must pass its own lint."""
    findings = [f for path in TEMPLATE_SRC.rglob("*.ts*") for f in lint_source(path.read_text(), path)]
    assert findings == []


def test_cli_searches_folders_and_fails_on_errors(tmp_path: Path, run_script: Callable[..., dict[str, Any]]) -> None:
    scenes = tmp_path / "src" / "scenes"
    scenes.mkdir(parents=True)
    (scenes / "Good.tsx").write_text("export const a = (frame: number, fps: number) => frame / fps;\n")
    (tmp_path / "src" / "node_modules").mkdir()
    (tmp_path / "src" / "node_modules" / "dep.ts").write_text("Math.random();\n")  # dependencies are not ours to lint
    report = run_script("lint_scenes.py", str(tmp_path / "src"))
    assert (report["checked"], report["errors"]) == (1, 0)
    (scenes / "Bad.tsx").write_text("const x = Math.random();\n")
    with pytest.raises(RuntimeError):
        run_script("lint_scenes.py", str(tmp_path / "src"))
