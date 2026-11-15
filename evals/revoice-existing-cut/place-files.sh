#!/usr/bin/env bash
# Copies the project and synthesizes its two narration takes (needs python3 and ffmpeg).
set -eu
cp -R "$(dirname "$0")/files/." .
python3 make_takes.py
rm make_takes.py
