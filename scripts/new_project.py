"""Create a video project from the skill's Remotion template.

Copies the template, makes the asset folders, fills in project.md, installs the
pinned packages and makes the first git commit.

Usage: new_project.py NAME [--title "Readable title"] [--parent ~/Movies/video-projects] [--no-install]
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent.parent / "template"
ASSET_FOLDERS = ("narration", "music", "sfx", "footage", "images", "fonts")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("name", help="folder name: lowercase letters, digits and dashes")
    parser.add_argument("--title")
    parser.add_argument("--parent", type=Path, default=Path.home() / "Movies" / "video-projects")
    parser.add_argument("--no-install", action="store_true")
    args = parser.parse_args()

    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", args.name):
        sys.exit(f"Project name {args.name!r} must be lowercase letters, digits and dashes")
    project = args.parent.expanduser() / args.name
    if project.exists():
        sys.exit(f"{project} already exists; open it instead of creating it")

    shutil.copytree(TEMPLATE, project, ignore=shutil.ignore_patterns("node_modules", ".DS_Store"))
    (project / "gitignore").rename(project / ".gitignore")
    brief = project / "project.md"
    brief.write_text(brief.read_text().replace("{{title}}", args.title or args.name))
    for folder in ASSET_FOLDERS:
        (project / "public" / "assets" / folder).mkdir(parents=True, exist_ok=True)
    (project / "scripts").mkdir()

    if not args.no_install:
        subprocess.run(["npm", "install", "--no-fund", "--no-audit"], cwd=project, check=True)
    subprocess.run(["git", "init", "--quiet"], cwd=project, check=True)
    subprocess.run(["git", "add", "-A"], cwd=project, check=True)
    subprocess.run(["git", "commit", "--quiet", "-m", "init: project from video-producer template"], cwd=project, check=True)
    print(project)


if __name__ == "__main__":
    main()
