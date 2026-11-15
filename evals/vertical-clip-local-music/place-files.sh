#!/usr/bin/env bash
# Synthesizes the soft chord pad the brief calls music.mp3 (needs ffmpeg), so the case holds no binary files.
set -eu
ffmpeg -v error -y -f lavfi \
  -i "aevalsrc='0.12*(sin(2*PI*220*t)+sin(2*PI*277.18*t)+sin(2*PI*329.63*t))*(0.6+0.4*sin(2*PI*0.25*t))*min(1,t/1.5)':s=44100:d=20" \
  -ac 2 -c:a libmp3lame -b:a 192k music.mp3
