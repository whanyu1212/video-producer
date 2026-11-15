"""Synthesize a basic sound effect with ffmpeg: free, instant and the same every run.

For UI-style motion graphics (ticks, whooshes, hits, risers) these cover the common
moments without spending credits. They are simple tones and filtered noise; when a
hero moment needs a richer sound, generate it with sfx.py (about 200 credits).

Each effect is rendered, measured, then gained so its true peak sits at --peak dBTP
(a limiter alone overshot by up to 2 dB in testing), so it is clearly audible in the mix.

Writes, never overwriting earlier takes:
  <out-dir>/<name>_vN.wav       the effect
  <out-dir>/<name>_vN.gen.json  the preset and ffmpeg graph, so it can be remade

Usage: synth_sfx.py PRESET [--name NAME] [--peak -3] [--out-dir public/assets/sfx]
       synth_sfx.py --list
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from elevenlabs_api import next_take, write_sidecar
from media import measure_loudness, run

RATE = 48000


@dataclass(frozen=True)
class Preset:
    description: str
    duration_s: float
    sources: tuple[str, ...]
    """lavfi sources, one ffmpeg input each."""
    graph: str
    """-filter_complex graph over the inputs, ending in [out]."""


PRESETS: dict[str, Preset] = {
    "tick": Preset("short bright UI tick, 60 ms", 0.06,
                   (f"aevalsrc='sin(2*PI*2400*t)*exp(-90*t)':d=0.06:s={RATE}",), "[0]anull[out]"),
    "blip": Preset("rising two-tone digital blip, 0.18 s", 0.18,
                   (f"aevalsrc='sin(2*PI*(900+2600*t)*t)*exp(-14*t)':d=0.18:s={RATE}",), "[0]anull[out]"),
    "chime": Preset("bell-like confirmation chime, 0.96 s with its echo", 0.96,
                    (f"aevalsrc='(0.6*sin(2*PI*1318*t)+0.35*sin(2*PI*1976*t)+0.2*sin(2*PI*2637*t))*exp(-5*t)':d=0.9:s={RATE}",),
                    "[0]aecho=0.8:0.5:60:0.3[out]"),
    "whoosh": Preset("airy band-passed whoosh, 0.6 s", 0.6,
                     (f"anoisesrc=d=0.6:c=pink:a=0.9:r={RATE}:s=7",),
                     "[0]bandpass=f=1800:width_type=o:w=2.5,afade=t=in:d=0.25:curve=exp,afade=t=out:st=0.25:d=0.35:curve=exp[out]"),
    "impact": Preset("sub drop with a noise crack, for a title landing, 1.4 s", 1.4,
                     (f"aevalsrc='sin(2*PI*(48+70*exp(-8*t))*t)*exp(-2.6*t)':d=1.4:s={RATE}",
                      f"anoisesrc=d=1.4:c=white:a=0.6:r={RATE}:s=7"),
                     "[1]highpass=f=2500,afade=t=out:st=0:d=0.12[crack];[0][crack]amix=inputs=2:normalize=0[out]"),
    "riser": Preset("noise swell that brightens into a hit, 1.6 s", 1.6,
                    (f"anoisesrc=d=1.6:c=pink:a=0.8:r={RATE}:s=7",),
                    "[0]highpass=f=600,afade=t=in:d=1.5:curve=qsin,afade=t=out:st=1.5:d=0.1[out]"),
    "swell": Preset("low airy drone that opens a piece, 3 s", 3.0,
                    (f"aevalsrc='0.5*sin(2*PI*55*t)+0.25*sin(2*PI*110.5*t)+0.15*sin(2*PI*220*t)':d=3:s={RATE}",
                     f"anoisesrc=d=3:c=brown:a=0.5:r={RATE}:s=7"),
                    "[1]lowpass=f=900[air];[0][air]amix=inputs=2:normalize=0,afade=t=in:d=1.8:curve=qsin,afade=t=out:st=2.2:d=0.8[out]"),
}


def render(preset: Preset, path: Path, gain_db: float = 0.0, codec: str = "pcm_s24le") -> None:
    """Render ``preset`` to ``path`` with ``gain_db`` applied after its graph."""
    inputs = [arg for source in preset.sources for arg in ("-f", "lavfi", "-i", source)]
    graph = preset.graph.replace("[out]", f",volume={gain_db:.2f}dB[out]")
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *inputs, "-filter_complex", graph,
         "-map", "[out]", "-ac", "1", "-ar", str(RATE), "-c:a", codec, str(path)])


def synthesize(preset: Preset, path: Path, peak_dbtp: float) -> float:
    """Render ``preset`` to ``path`` with its true peak at ``peak_dbtp``; return the gain applied in dB."""
    with tempfile.TemporaryDirectory() as scratch:
        raw = Path(scratch) / "raw.wav"
        # Float, so a graph that sums past full scale is measured, not clipped.
        render(preset, raw, codec="pcm_f32le")
        loudness = measure_loudness(raw)
    if loudness is None:
        sys.exit(f"could not measure the raw '{preset.description}' render")
    gain = peak_dbtp - loudness.true_peak_dbtp
    render(preset, path, gain)
    return round(gain, 2)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("preset", nargs="?", choices=sorted(PRESETS))
    parser.add_argument("--name", help="file stem; defaults to the preset name")
    parser.add_argument("--peak", type=float, default=-3.0, help="true peak to normalize to, dBTP")
    parser.add_argument("--out-dir", type=Path, default=Path("public/assets/sfx"))
    parser.add_argument("--list", action="store_true", help="print the presets and exit")
    args = parser.parse_args()
    if args.list:
        print(json.dumps({name: preset.description for name, preset in PRESETS.items()}, indent=2))
        return
    if args.preset is None:
        parser.error("give a PRESET or --list")

    preset = PRESETS[args.preset]
    path = next_take(args.out_dir, args.name or args.preset, ".wav")
    gain = synthesize(preset, path, args.peak)
    write_sidecar(
        path,
        tool="synth_sfx",
        request={"preset": args.preset, "sources": list(preset.sources), "graph": preset.graph, "gain_db": gain},
        credits_estimate=0,
    )
    measured = measure_loudness(path)
    print(json.dumps({
        "audio": str(path),
        "preset": args.preset,
        "duration_s": preset.duration_s,
        "true_peak_dbtp": measured.true_peak_dbtp if measured else None,
    }, indent=2))


if __name__ == "__main__":
    main()
