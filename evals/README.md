# Evals

Four briefs for judging a SKILL.md edit: run them with the old and the new skill and
compare. Each case folder uses the layout `claude plugin eval` and the skill-creator
skill read (`prompt.md`, `case.yaml`, `graders/`, and `place-files.sh` plus `files/`
where the case starts from existing material).

| Case | Brief | What it checks (SKILL.md) |
|---|---|---|
| `promo-15s-plan-first` | 15 s promo with voice and music, from nothing | Workflow 1 and 3: brief quoted, Look/Script/Plan filled, paid scripts only with `--dry-run`, estimate given, stops for the go-ahead |
| `vertical-clip-local-music` | 12 s 9:16 text clip with supplied music, no voice | Workflow 7 to 10 and the quality floor: render, `probe.py` clean, −14 LUFS / ≤ −1 dBTP, frames reviewed, text timing and safe margin, commit and tag |
| `revoice-existing-cut` | Swap a new take into a finished cut, no render | Iterating with the user, step 3: cuts re-measured in silence, length from the new take, cue `nth` on repeated words, levels moved by the measured shift |
| `walkthrough-scenes-from-recording` | Narrated walkthrough from a screen recording and a finished take, stills only | Workflow 2, 4, 6 and 7 and the Remotion rules: sources read first, labels timed from words, screens switched in measured silence, length from the speech end, frame-driven scenes that typecheck, a still read at each label with text size and contrast checked, any change to the voice-over put to the user |

The briefs are of unlike kinds on purpose (a promo, a text-only social clip, an explainer
re-voice, a screen-recording walkthrough), so a rule that only suits one kind of video
shows up as a regression in another. Keep that spread when adding a case.

## No credits

No case needs ElevenLabs. The scaffolds synthesize their media with ffmpeg (the
narration takes are tone bursts with exact silences, the re-voice v2 6 dB quieter than v1;
the recording is three flat screens drawn with boxes), so the
graders' numbers are known in advance. Every case has a grader that fails the run if
it generated anything. Run them with `ELEVENLABS_API_KEY` unset, no `elevenlabs-api-key`
Keychain item and the ElevenLabs MCP disconnected, so a slip fails instead of spending.

## Running

- **With the skill-creator skill** (the usual way): it reads these folders, runs each
  case with and without the skill, grades and opens the review viewer. For a case with
  `place-files.sh`, run that script in the run's empty working folder first.
- **With the CLI**, from the skill folder:
  `claude plugin eval . --allow-tools Write,Edit,Bash --scaffold`. Its sandbox blocks
  the npm registry, so only `revoice-existing-cut` runs properly this way: the three
  cases that create a project cannot install Remotion, and a run then scores low for
  that reason alone.

Either way these are billed model runs (not ElevenLabs credits), so ask before starting
them. Each case runs three times by default with the CLI (`--runs 1` for one).

Needs python3, ffmpeg with libmp3lame, and for the three cases that create a project,
npm with network access (`new_project.py` installs Remotion; the first render
downloads a headless browser).
