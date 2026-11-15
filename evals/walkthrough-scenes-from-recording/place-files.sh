#!/usr/bin/env bash
# Synthesizes the screen recording and the narration take the brief starts from
# (needs python3 and ffmpeg), so the case holds no binary files.
set -eu
here="$(cd "$(dirname "$0")" && pwd)"
cp "$here/files/script.txt" .

# Three 6 s "screens" drawn with boxes: a three-column board, one open card, a share dialog.
screen() { echo "color=c=$1:s=1920x1080:r=30:d=6,$2"; }
board="$(screen 0x1E293B "drawbox=x=120:y=160:w=500:h=800:color=0x334155:t=fill,drawbox=x=710:y=160:w=500:h=800:color=0x334155:t=fill,drawbox=x=1300:y=160:w=500:h=800:color=0x334155:t=fill,drawbox=x=160:y=220:w=420:h=140:color=0xF8FAFC:t=fill")"
card="$(screen 0x0F172A "drawbox=x=360:y=140:w=1200:h=800:color=0xF8FAFC:t=fill,drawbox=x=440:y=240:w=700:h=60:color=0x94A3B8:t=fill,drawbox=x=440:y=620:w=1040:h=220:color=0xE2E8F0:t=fill")"
share="$(screen 0x475569 "drawbox=x=610:y=340:w=700:h=400:color=0xF8FAFC:t=fill,drawbox=x=1050:y=640:w=200:h=60:color=0xF59E0B:t=fill")"
ffmpeg -nostdin -v error -y -f lavfi -i "$board" -f lavfi -i "$card" -f lavfi -i "$share" \
  -filter_complex "[0][1][2]concat=n=3:v=1[v]" -map "[v]" -c:v libx264 -pix_fmt yuv420p recording.mp4

# The take: tone bursts with exact silences (the re-voice case's generator; only its v1 pace is used).
python3 "$here/../revoice-existing-cut/files/make_takes.py"
mv public/assets/narration/narration_v1.mp3 narration.mp3
mv public/assets/narration/narration_v1.words.json narration.words.json
rm -r public
