"""Synthesize the two narration takes this eval starts from, so it needs no credits and no binary files.

Each word is a short tone burst and the gaps between words are digital silence,
so every cut point and loudness figure is known exactly. Take v2 is slower and
6 dB quieter than v1, like a calmer read replacing a brighter one.
Writes public/assets/narration/narration_v{1,2}.mp3 and .words.json (needs ffmpeg).
"""

import json
import math
import struct
import subprocess
import wave
from pathlib import Path

RATE = 22050
FADE_S = 0.01
OUT = Path("public/assets/narration")
SCRIPT = Path("script.txt")
TAKES = {
    "narration_v1": {"lead": 0.15, "word": 0.28, "gap": 0.06, "sentence": 0.35, "paragraph": 0.5, "amplitude": 0.5},
    "narration_v2": {"lead": 0.2, "word": 0.32, "gap": 0.08, "sentence": 0.45, "paragraph": 0.6, "amplitude": 0.25},
}


Word = tuple[str, float, float]


def layout(paragraphs: list[list[str]], pace: dict[str, float]) -> list[Word]:
    words: list[Word] = []
    t = pace["lead"]
    for p, paragraph in enumerate(paragraphs):
        for i, text in enumerate(paragraph):
            words.append((text, round(t, 3), round(t + pace["word"], 3)))
            t += pace["word"]
            last_in_paragraph = i == len(paragraph) - 1
            if last_in_paragraph and p < len(paragraphs) - 1:
                t += pace["paragraph"]
            elif text[-1] in ".?!":
                t += pace["sentence"]
            elif not last_in_paragraph:
                t += pace["gap"]
    return words


def write_take(name: str, words: list[Word], amplitude: float) -> None:
    end = words[-1][2] + 0.6
    samples = [0.0] * round(end * RATE)
    for _, start, stop in words:
        a, b = round(start * RATE), round(stop * RATE)
        for n in range(a, b):
            t = (n - a) / RATE
            envelope = min(1.0, t / FADE_S, (b - n) / RATE / FADE_S)
            samples[n] = amplitude * envelope * (0.7 * math.sin(2 * math.pi * 220 * t) + 0.3 * math.sin(2 * math.pi * 440 * t))
    wav = OUT / f"{name}.wav"
    with wave.open(str(wav), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(RATE)
        out.writeframes(b"".join(struct.pack("<h", round(s * 32767)) for s in samples))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(wav), "-c:a", "libmp3lame", "-b:a", "128k", str(OUT / f"{name}.mp3")], check=True)
    wav.unlink()
    timings = [{"text": text, "start": start, "end": stop} for text, start, stop in words]
    (OUT / f"{name}.words.json").write_text(json.dumps(timings, indent=1) + "\n")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    paragraphs = [p.split() for p in SCRIPT.read_text().strip().split("\n\n")]
    for name, pace in TAKES.items():
        write_take(name, layout(paragraphs, pace), pace["amplitude"])


if __name__ == "__main__":
    main()
