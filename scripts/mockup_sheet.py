"""Tile rendered stills into one comparison sheet the user can pick from.

Writes two files:
  <out>.png   the stills in a grid, row by row, each fitted into an equal cell
              (mixed 16:9 and 9:16 stills keep their shape, padded with grey)
  <out>.html  a self-contained page (images and audio inlined) with each still's
              label and note, plus optional audio clips such as voice previews

This ffmpeg may have no drawtext filter, so the PNG carries no text: draw the
option's name inside the mock-up composition itself, or send the HTML. The JSON
printed lists every cell's label in order.

Usage: mockup_sheet.py IMAGE[=LABEL]... [--note TEXT]... [--audio FILE[=LABEL]]...
                       [--title TEXT] [--intro TEXT] [--cols 2] [--cell-width 960]
                       [--cell-height H] [--out out/mockups/sheet]
"""

from __future__ import annotations

import argparse
import base64
import html
import json
import math
import mimetypes
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from media import ffprobe, run

GAP = 12
FILL = "0x555555"


@dataclass(frozen=True)
class Item:
    path: Path
    label: str
    note: str = ""


def parse_item(arg: str) -> Item:
    """Split ``PATH=LABEL``; the label defaults to the file's stem."""
    path, _, label = arg.partition("=")
    return Item(Path(path), label.strip() or Path(path).stem)


def grid_size(count: int, cols: int) -> tuple[int, int]:
    """Columns and rows for ``count`` cells, never wider than needed."""
    cols = max(1, min(cols, count))
    return cols, math.ceil(count / cols)


def tile_filter(count: int, cols: int, width: int, height: int) -> str:
    """filter_complex that fits each input into a ``width``×``height`` cell and grids them with gaps."""
    cells = [
        f"[{i}:v]scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color={FILL},"
        f"pad={width + GAP}:{height + GAP}:{GAP}:{GAP}:color={FILL},format=rgb24[c{i}]"
        for i in range(count)
    ]
    if count == 1:
        return ";".join(cells) + f";[c0]pad=iw+{GAP}:ih+{GAP}:0:0:color={FILL}[out]"
    layout = "|".join(f"{(i % cols) * (width + GAP)}_{(i // cols) * (height + GAP)}" for i in range(count))
    stack = "".join(f"[c{i}]" for i in range(count)) + f"xstack=inputs={count}:layout={layout}:fill={FILL}"
    return ";".join(cells) + f";{stack},pad=iw+{GAP}:ih+{GAP}:0:0:color={FILL}[out]"


def data_uri(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()


def render_html(title: str, intro: str, images: list[Item], audio: list[Item], uri: Callable[[Path], str] = data_uri) -> str:
    """The comparison page; ``uri`` turns a file into the ``src`` it is embedded with."""
    esc = html.escape
    figures = "\n".join(
        f'<figure><img src="{uri(item.path)}" alt="{esc(item.label)}">'
        f"<figcaption><strong>{esc(item.label)}</strong>{' ' + esc(item.note) if item.note else ''}</figcaption></figure>"
        for item in images
    )
    clips = "\n".join(
        f'<article class="clip"><h3>{esc(item.label)}</h3><audio controls preload="auto" src="{uri(item.path)}"></audio></article>'
        for item in audio
    )
    listen = f'<h2>Listen</h2>\n<div class="clips">{clips}</div>' if audio else ""
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<style>
:root {{ --bg:#F6F4F1; --card:#FFFFFF; --ink:#26232B; --muted:#6A6470; --line:#E3DED8; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#1C1A1F; --card:#27242B; --ink:#F1EEF4; --muted:#B4ADBB; --line:#38343D; }} }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--ink); font:16px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif; }}
main {{ max-width:1080px; margin:0 auto; padding:32px 16px 64px; }}
h1 {{ font-size:28px; margin:0 0 4px; }} h2 {{ font-size:21px; margin:32px 0 8px; }}
.intro {{ color:var(--muted); margin:0 0 16px; }}
figure {{ margin:0 0 20px; background:var(--card); border:1px solid var(--line); border-radius:14px; overflow:hidden; }}
figure img {{ width:100%; max-height:80vh; object-fit:contain; display:block; background:#555; }}
figcaption {{ padding:12px 16px; font-size:15px; }}
.clips {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(260px,1fr)); gap:12px; }}
.clip {{ background:var(--card); border:1px solid var(--line); border-radius:14px; padding:12px 16px; }}
.clip h3 {{ margin:0 0 8px; font-size:16px; }} audio {{ width:100%; }}
</style></head>
<body><main>
<h1>{esc(title)}</h1>
{f'<p class="intro">{esc(intro)}</p>' if intro else ""}
{figures}
{listen}
</main></body></html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("images", nargs="+", metavar="IMAGE[=LABEL]")
    parser.add_argument("--note", action="append", default=[], help="note under each image, in image order")
    parser.add_argument("--audio", action="append", default=[], metavar="FILE[=LABEL]", help="clip for the page only")
    parser.add_argument("--title", default="Options")
    parser.add_argument("--intro", default="", help="line under the page title")
    parser.add_argument("--cols", type=int, default=2)
    parser.add_argument("--cell-width", type=int, default=960)
    parser.add_argument("--cell-height", type=int, help="default: from the first image's shape")
    parser.add_argument("--out", type=Path, default=Path("out/mockups/sheet"), help="path without extension")
    args = parser.parse_args()

    if len(args.note) > len(args.images):
        sys.exit(f"{len(args.note)} notes for {len(args.images)} images")
    notes = args.note + [""] * (len(args.images) - len(args.note))
    images = [Item(item.path, item.label, note) for item, note in zip(map(parse_item, args.images), notes, strict=True)]
    audio = [parse_item(arg) for arg in args.audio]
    missing = [str(item.path) for item in images + audio if not item.path.is_file()]
    if missing:
        sys.exit(f"Not found: {', '.join(missing)}")

    first = next(s for s in ffprobe(images[0].path)["streams"] if s["codec_type"] == "video")
    height = args.cell_height or round(args.cell_width * first["height"] / first["width"] / 2) * 2
    cols, rows = grid_size(len(images), args.cols)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    png = args.out.with_suffix(".png")
    inputs = [arg for item in images for arg in ("-i", str(item.path))]
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *inputs,
         "-filter_complex", tile_filter(len(images), cols, args.cell_width, height),
         "-map", "[out]", "-frames:v", "1", str(png)])
    page = args.out.with_suffix(".html")
    page.write_text(render_html(args.title, args.intro, images, audio))

    print(json.dumps({
        "png": str(png),
        "html": str(page),
        "html_mb": round(page.stat().st_size / 1e6, 2),
        "grid": f"{cols}x{rows}",
        "cells": [
            {"row": i // cols + 1, "col": i % cols + 1, "label": item.label, "image": str(item.path)}
            for i, item in enumerate(images)
        ],
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
