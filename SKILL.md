---
name: video-producer
description: >-
  Produce short videos end to end with Remotion, ffmpeg and ElevenLabs: product
  promos, explainers, launch videos, social clips (9:16 / 1:1), animated motion
  graphics, narrated walkthroughs of screen recordings, thumbnails. Plans the
  piece, writes the scenes as React code, generates narration, music and sound
  effects, renders, measures (loudness, dead frames, length) and reviews its own
  frames before delivering. Use when the user asks to make, edit, re-cut or
  re-render a video, add narration/voice-over, music or captions, or turn a
  recording, docs site or idea into a video.
---

# Video producer

You are the director and editor. Remotion is the timeline (scenes are React
code, timed in frames), ffmpeg does measurement and delivery, ElevenLabs makes
voice, music and effects. Your job is taste plus discipline: decide the piece,
then make it exact, measured and versioned.

`V=~/.claude/skills/video-producer/scripts` below. Every script takes `--help`.

| Need | Command |
|---|---|
| New project | `python3 $V/new_project.py NAME --title "…"` → `~/Movies/video-projects/NAME` (Remotion + git, packages installed) |
| What a file holds | `python3 $V/probe.py FILE` → length, fps, size, LUFS, true peak, still/black stretches (dark frames that still hold content listed apart), how much the last 0.25 s still moves, warnings; `--timeline` adds loudness second by second and warns when it spans over 6 LU |
| See a video | `python3 $V/contact_sheet.py FILE` then read the PNG; `python3 $V/extract_frame.py FILE 4.5 last` for full-size frames |
| Options to pick from | `python3 $V/mockup_sheet.py out/mockups/A.png="A · Soft" out/mockups/B.png="B · Minimal" [--audio clip.mp3="Voice A"] --out out/mockups/options` → one grid PNG plus a self-contained HTML page with labels and clips |
| Narration + word times | `python3 $V/narrate.py --voice ID --script script.txt [--dry-run --target-seconds 60]` (the dry run gives the read time and the speed that fits) |
| Narration made with the MCP (no key) | `python3 $V/import_mcp_narration.py --audio-url URL --words-url URL --voice ID --script script.txt` (see Narration via the MCP) |
| Music to a plan | `python3 $V/compose_music.py --plan plan.json [--dry-run]` |
| Music made with the MCP (no key) | `python3 $V/import_mcp_music.py --audio-url URL --prompt "…" --duration 30 --model ID --credits N` (steps in its `--help`) |
| Beat grid of a music bed | `python3 $V/music_beats.py MUSIC [--near 12.4]` → tempo, beat times and the nearest beat to each planned cut; no grid when the beat is weak |
| Free sound effect | `python3 $V/synth_sfx.py whoosh` (`--list`: tick, blip, chime, whoosh, impact, riser, swell) → `public/assets/sfx/whoosh_vN.wav` at −3 dBTP |
| Generated sound effect | `python3 $V/sfx.py --text "…" --name NAME [--dry-run]` |
| Words of existing speech | `python3 $V/transcribe.py FILE` |
| Check cues against a take | `python3 $V/check_cues.py public/assets/narration/narration_vN.words.json --script script.txt --src src` → words spoken more than once with each `nth`, script/take mismatches, cues that miss or take the first of several |
| Cut points in silence | `python3 $V/silence_cuts.py TAKE.mp3 --words TAKE.words.json --after "pricing." --at 34.5` → the nearest cut at ≤ −60 dBFS for each; `--threshold -35` gives `speech_end_s` |
| Levels for a new take | `python3 $V/match_levels.py OLD.mp3 NEW.mp3 --db -9 --volume 0.09` → the loudness shift and each music (dB) and effect (linear) level moved by it |
| First frames after each cut | `python3 $V/cut_frames.py out/vN.mp4 --at 4.35 --at 9.48` → `out/cuts.png`, a row per cut |
| Still against the render | `python3 $V/frame_diff.py out/f_120.png out/vN.mp4 --frame 120` → mean and worst-block difference; warns when something reaches the frame late |
| Even out an uneven take | `python3 $V/level_take.py TAKE.mp3` → `TAKE_level.wav`, same timing, narrower loudness spread (opt-in; listen for pumping) |
| Delivery loudness | `python3 $V/loudnorm_export.py out/vN.mp4 out/NAME_vN.mp4` → which mode ran and why; `--limit` for peaky speech (`--replace` only for an export nobody was sent) |
| Scene code check | `python3 $V/lint_scenes.py src` → randomness, timers, clocks, CSS motion (errors), plain HTML media and frame-number timing (warnings) |
| References and house style | `python3 $V/refs.py genres`, `list --genre D1`, `show ID`, `study ID`, `house` (steps in `review/taste.md`) |
| Preview a frame | `npx remotion still src/index.ts Main out/f_120.png --frame=120` |
| Render | `npx remotion render src/index.ts Main out/vN.mp4` (`--frames=0-299`, `--scale=0.5` for drafts) |
| Let the user scrub | `npm run studio` |

Run scripts from the project folder: outputs default to `public/assets/…` and `out/`.

## Workflow

1. **Brief.** Create the project, then fill `project.md`: quote the request
   word for word; settle length, aspect ratio(s), where it will be watched,
   voice or not, and the one takeaway. Ask only what you cannot decide.
2. **Understand the material.** Probe every source file. Read footage as
   contact sheets before planning cuts, and pull exact frames for anything you
   will reuse. Read brand assets and docs the user points to.
3. **Plan, then show it.** Write Look (idea, palette as hex, type, motion feel,
   sound), Script and the Plan table (beat by beat with times and sources).
   Run the paid scripts with `--dry-run` and give the user the plan plus the
   credit estimate. **Never spend credits without the user's go-ahead.**
   Fit the script to the length before paying: `narrate.py --dry-run
   --target-seconds N` gives the read time and the speed that fits; past its
   range, cut or add words, so a take is not paid for twice to change its length.
   For a piece with a look to decide, read the house style and offer reference
   candidates from the library with the plan, so the user picks them with the
   go-ahead (`review/taste.md`).
4. **Voice first.** Narration fixes the timing of everything else. Pick a
   voice with the ElevenLabs MCP (search/preview voices) and pass its
   `voice_id` to `narrate.py`, or narrate through the MCP when there is no
   API key (see Narration via the MCP). Set `DURATION_SECONDS` from the
   measured speech end plus the outro, never from an estimate. Both routes
   print the take's loudness: note it in Decisions, because music and effect
   levels are set against it (takes have come back from −34 to −19 LUFS).
   `probe.py TAKE --timeline` shows whether it is even: when it warns (some
   lines over 6 LU louder than others), make a levelled copy with
   `level_take.py`, send the user both clips and let them choose; the take
   stays in use until they pick the copy.
   Pace the read with `pauses` on the narration in `src/timeline.ts` rather
   than with a retake, each at a cut where `silence_cuts.py` finds silence;
   this is also how a take that came back short reaches its length. Measure
   cuts on the take as generated, not on a copy raised in level, and follow its
   noise-floor warning when it gives one.
5. **Music and effects.** Compose music as plan chunks whose `duration_ms`
   match the beats (instrumental: section name only in `text`, `vocals` in
   `negative_styles`), or use a free track and record its source and licence
   in Decisions. Prefer free effects: `synth_sfx.py` covers UI ticks,
   whooshes, hits and risers; generate with `sfx.py` only what is missing, such
   as a richer hero sound. Keep every effect in `effects` in `src/timeline.ts`
   (`src`, `at`, `volume`, and a comment naming the action it marks). To cut on
   the music, take beat times from `music_beats.py`; when it prints no grid,
   time those cuts by hand from the music plan.
6. **Build scenes.** One component per beat family in `src/scenes/`, reused
   through props. Start each new scene file with a short art-direction comment
   (what it shows, palette, motion). Time animation from the voice:
   `cue("launch")` from `src/timeline.ts` (words on the video timeline, lead-in
   and pauses applied), not hand-typed seconds.
7. **Preview cheaply.** Render stills at the key frame of each beat and look
   at them before any full render. Fix layout on stills; only then render
   motion, as a draft (`--scale=0.5`) if the video is long.
8. **Review like an editor.** On every render: `probe.py` (fix every warning),
   a contact sheet, the last frame, and stills wherever something moves fast
   or text appears. Read the frames yourself and check the list below. Stills
   show layout, not how long something stays: for each beat's payoff (what its
   line builds to), work out from the source the time from the cue that reveals
   it to the moment its scene starts to leave, and hold it to the reading time
   below. A contact sheet also misses what happens at a cut: run
   `cut_frames.py` with every beat start and check that each row opens on
   something (the first cell of a row is the old beat, except for a beat
   starting at 0). No tool hears the mix:
   run `probe.py --timeline` on the render, settle its spread warning, and say
   in the report that the sound was checked on meters only. Fix, re-render,
   re-check. Then, once per round, a critic that did not make the cut compares
   its frames with the brief and the picked references (`review/taste.md`, step
   3); skip it when no subagent can be started, and say so.
   User feedback on a cut starts a new round (see Iterating with the user).
9. **Version.** Each delivered cut is a commit and a tag:
   `git add -A && git commit -m "v2: tighter intro" && git tag v2` (`-A` so
   new scenes and `.gen.json` records are included). Log it in the Versions
   table with its length and loudness. Generated media is never overwritten:
   scripts write `_v1`, `_v2`… takes with a `.gen.json` record of the request.
10. **Deliver.** Only once step 8 passes on the final render: `loudnorm_export.py`
    never overwrites, so an export made before a fix stays behind under the
    delivery name. If a later check still finds a fault and the export was never
    sent to anyone, re-export with `--replace`; a file the user has seen gets
    the next version number instead. Final render → `loudnorm_export.py` (−14 LUFS for YouTube and
    social, −16 podcast, −23 broadcast; true peak ≤ −1 dBTP) → `probe.py` on
    the delivered file → `extract_frame.py … last`. The export says whether
    loudnorm could apply one gain (linear) or rode it (dynamic): a dynamic
    warning about peaks means re-export with `--limit` and tell the user how many
    dB the limiter took off, and that nobody has heard it yet (no tool listens);
    one about the loudness range means fixing the uneven part of the mix. Other shapes come from the
    same scenes: render the `Vertical` composition (or add a square one);
    scenes size from `Math.min(width, height)`, so re-check layout on stills.
    Render the `Thumbnail` still and check it at ~170 px wide. Report the file
    path, length, loudness and anything you could not fix.

## Quality floor (measure, don't eyeball)

- Every tool warning is a defect to fix or to explain to the user.
- No still stretch over 0.5 s unless it is a deliberate hold; held cards keep a
  slow drift. `probe.py` measures change across the whole frame, so a hold where
  only small things move (particles, a glow) can still be listed: look at one
  frame of each and name the ones you keep. No unplanned black frames. `probe.py` lists dark stretches whose
  frames still hold content (a caption on a dark design) under `dark`, with no
  warning: look at one frame of each.
- Animation finishes before its beat ends; the last frame is settled, not mid-move
  (`probe.py` measures the last 0.25 s; ambient drift, grain or a loop is fine).
- Every beat opens on content: at its first frame something is already there or
  arriving. Start the first element just before the cut, or move the cut onto the
  first word that has a visual.
- Text: on screen long enough to read twice (~0.3 s per word, 1.2 s minimum),
  inside a 5% safe margin, never cropped. On 9:16 keep captions and anything
  that must be read out of the bottom 15%, where TikTok and Reels draw their own
  buttons and text (the template's captions already sit above it). Legible at phone size: captions and
  other text meant to be read are at least 5% of the frame's short side as
  rendered (54 px at 1080, after any scale on a parent), secondary text at
  least 3% (32 px). Check on a still shrunk to 480 px wide.
- Cuts land on the voice or the beat, at measured times. A cut meant for a
  music beat lands within 0.1 s (3 frames) of where that beat measures.
- Sound: speech clearly above music (the template ducks music under narration),
  no clipping, loudness on target. With inserted pauses, set the music's
  `duckThrough` above the longest gap between words that the music should stay
  down through (the take's own silence plus the inserted pause, measured on
  the timeline `words`), or the music swells in every pause. Every effect can be heard in the render: a
  file whose true peak is below −12 dB (`probe.py`) is replaced or boosted.
- Facts, spoken or on screen: a number, name or claim the viewer will read as
  true is checked against a source, or it is plainly an illustration; record
  which in Decisions and tell the user about every illustrative one. For health,
  money or legal subjects, list the sources in `project.md` and settle with the
  user whether the video says it is not professional advice. When the primary
  source cannot be opened (a bot check, a paywall), never work around the block:
  use reports that quote it and agree with each other, and say so in Decisions
  and to the user.
- Footage: crops keep the subject; no personal data visible (paths, emails,
  keys, names) unless the user wants it shown.
- Drawn figures, icons and diagrams: zoom into each one on a full-size still,
  in every pose and shape used. Parts that belong together touch (a head on
  its neck, a hand on its arm, a pointer on its label), nothing floats or is
  cut off, and every colour stands out against every background it crosses.
  A contact sheet is too small to show these.

## Motion defaults

Starting points, in seconds so they hold at any frame rate. Depart from one on
purpose, for a reason you can name, not by accident.

- **Length.** Something arriving takes about 0.4 s; a fade alone about 0.2 s;
  something leaving 0.3-0.5 s. Under 0.2 s or over 0.8 s is a choice to justify.
- **Easing.** Arrivals decelerate (ease out), exits accelerate (ease in).
  Nothing moves at a constant rate except a slow drift on a hold.
- **Overshoot.** At most one visible spring or overshoot in a video, small
  (under 10%) and late in the move.
- **Entrances move.** An element arrives with a small shift or scale; opacity
  helps for the first 0.15-0.2 s and is never the whole entrance.

Check them in the source before rendering: read every `interpolate` range,
easing and `spring` in the scenes against this list.

## Iterating with the user

Feedback on a delivered cut is a new round of the workflow, not a patch.

1. **Show options before a redesign.** When the user dislikes the look or the
   voice, mock it up before spending credits or rebuilding scenes. Register
   2-3 temporary compositions (`MockupA`, `MockupB`…) that draw the same
   moment in each style, render them as stills, tile them with
   `mockup_sheet.py`, send the sheet, and let the user pick. The PNG holds no
   text (this ffmpeg has no `drawtext`), so each mock-up draws its own name;
   the HTML page labels every still and can carry voice clips with
   `--audio`. Audition voices from the preview links that
   `creative_list_voices` returns (free) before generating a take. Keep the
   mock-ups in `src/mockups/` and record the choice in Decisions and the house
   style (`review/taste.md`, step 4); once a look is chosen, take their
   compositions out of `src/Root.tsx`.
2. **Price the round.** Re-voicing or re-composing spends credits: give the
   estimate and wait for the go-ahead, as in step 3.
3. **Re-voicing an existing cut.** A new take moves every timing.
   - Generate it as the next `_vN` take; keep the old one for comparison.
   - Re-time everything from the new word list, then run `check_cues.py` on
     it with `--script` and `--src`. A cue on a word spoken twice needs its
     occurrence number (`cue('When', 1)`), or it fires early: settle every
     warning it prints, and any script/take mismatch, before rendering.
   - Add pace with silence, not retakes: insert `pauses` at paragraph breaks,
     which plays the take as slices. Cut only where `silence_cuts.py --after WORD`
     (or `--at SECONDS`) finds silence (RMS ≤ −60 dBFS over 50 ms) and fix
     every warning it prints; a cut outside silence clips a breath.
   - Re-fit the music to the new length with `atempo` (old length ÷ new
     length; stay within about ±8 %, or compose a new bed). Check that its
     changes still land on their cue words.
   - Match levels: `match_levels.py OLD NEW --db <music baseDb> --volume
     <each effect volume>` measures both takes' integrated loudness and
     prints the levels moved by the difference, so speech keeps the same
     lead over the music and effects.
4. **Feedback during a render.** Stop the render, reproduce the problem on a
   still at the frame the user means, fix it, show the corrected still, then
   re-render. Look for the same defect in every other scene, pose and shape.
5. **Close the round.** Run the full review (step 8) and delivery (step 10)
   again, then commit, tag and log it as the next version, noting in Decisions
   what the user asked for and what changed.

## Remotion rules

- Everything is a function of `useCurrentFrame()`. No CSS transitions or
  animations, no `Math.random()` (use `random('seed')` from `remotion`), no
  timers: renders must be identical every time.
- Media lives in `public/assets/` and is referenced with `staticFile('assets/…')`.
  Footage: `<OffthreadVideo src={staticFile(…)} />` inside a `<Sequence>`.
- Wire narration, music and effects in `src/timeline.ts`:
  ```ts
  import takeWords from '../public/assets/narration/narration_v1.words.json';
  export const soundtrack: Soundtrack = {
    narration: {
      src: 'assets/narration/narration_v1.mp3', at: 0.5, words: takeWords,
      pauses: [{after: 12.4, seconds: 0.5}], // after "pricing.": silence_cuts.py
    },
    music: {src: 'assets/music/music_v1.mp3', baseDb: -8, duckDb: 10, fadeOut: 1.5, duckThrough: 1.2}, // longest gap between words: 1.0 s
    effects: [
      {src: 'assets/sfx/whoosh_v1.wav', at: 3.8, volume: 0.5}, // title slides in
    ],
  };
  ```
  `timeline.ts` then exports `words` (on the video timeline) and `cue()`;
  captions are `<WordCaptions words={words} />`.
- Run `npm run typecheck` and `lint_scenes.py src` after editing scenes. Fix every
  error; fix each warning or say why it is deliberate.
- Remotion is free for individuals and companies of up to 3 people; larger
  companies need a Remotion company licence. Mention it if the user is a company.

### With the official Remotion skills

When the `remotion-*` skills are installed (`npx skills add remotion-dev/skills -g`),
read their rule files for component APIs: `remotion-markup` for transitions,
sequencing, text measuring, local fonts, effects and embedding footage. This
skill still decides how the video is made. Where they disagree, this skill wins:

| Topic | The Remotion skills say | Do this instead |
|---|---|---|
| New project | `npx create-video` | `new_project.py`: the template carries the soundtrack, captions and both shapes |
| Rendering | Open Studio; render only when the user is very explicit | Stills, renders and the review of Workflow 7-10 on every cut. Start Studio when the user wants to scrub |
| Voice-over | Call ElevenLabs from a script, one MP3 per scene, no word times | `narrate.py` or the MCP after the go-ahead: one take with word times (Workflow 3-4) |
| Length | `calculateMetadata` sums the scene audio | `DURATION_SECONDS` from the measured speech end |
| Captions | `Caption` (`startMs`, `endMs`) from `@remotion/captions` | The `.words.json` shape (`text`, `start`, `end`) that `wordStart()` and `check_cues.py` read |
| Sound and footage | `Audio` and `Video` from `@remotion/media` | The template's `Audio` and `OffthreadVideo` from `remotion`: ducking passes `volume` a function of the frame, which is untested with `@remotion/media` |

### 3D with `@remotion/three` (provisional)

Real 3D adds packages: mock a 3D option with CSS perspective first, and install
only for a look the user has picked and with their OK. Then:

- Install `@remotion/three` at the project's pinned Remotion version, plus `three`,
  `@react-three/fiber` (8.x with React 18) and `@types/three`, all `--save-exact`,
  and add `Config.setChromiumOpenGlRenderer('angle')` to `remotion.config.ts`.
- `<ThreeCanvas>` needs `width` and `height`, and reads its `camera` prop once, when
  it is created. Set a moving camera inside the canvas on every render
  (`camera.position.set(…)`, `camera.lookAt(…)`, `camera.updateMatrixWorld()`), or
  every camera move is silently ignored.
- Everything a frame needs must exist at the first draw: lights and materials as
  elements, never added to the scene from an effect. Hold the render with
  `delayRender` until fonts load and the scene has mounted, and release it from
  a child of the canvas.
- A still is not proof of the render. For one frame in each 3D beat, run
  `frame_diff.py` on a fresh `remotion still --frame=N` and the render, and
  settle its warning.
- `flat` on the canvas turns off tone mapping, so whites and brand tints stay exact.
- Text on 3D objects: draw it into a `CanvasTexture` after the fonts load and cache
  it by content. Tilted or distant text shrinks fast, so check it at 480 px wide.
- Many objects: one `instancedMesh` with an opaque material; transparent
  instances sort wrongly.
- Other shapes: a three.js camera's field of view is vertical, so a narrower
  frame crops the sides of the scene while HTML overlays reflow. Frame each
  shape on its own (camera distance or staging from the aspect ratio) and check
  `Vertical` stills before offering that cut.
- Time a 3 s draft before building a heavier scene (glass tiles at 1080p:
  about 1 s of render per second of video).

## Costs and keys

- ElevenLabs credits (approximate): narration ~1 per character (Flash/Turbo
  cheaper), music ~900 per minute, effects ~200 each. Every paid script has
  `--dry-run`. Budget 2-3× for retakes.
- The scripts read the key from `ELEVENLABS_API_KEY` or the macOS Keychain
  (`security add-generic-password -s elevenlabs-api-key -a "$USER" -w`, which
  prompts for it). Never print, log or commit the key.
- The ElevenLabs MCP (OAuth, same account and credits) is for browsing voices,
  auditioning, and narration and music when there is no key. Music plans,
  seeded retakes and generated effects come from the scripts: the MCP's music
  takes one prompt and a total length (no timed sections) and its speech has no
  seed. For music through the MCP, read the model's parameters with
  `creative_get_model_schema`, run the node with `generations_count: 1` (music
  defaults to 4 variations, each billed), then save it with `import_mcp_music.py`.

## Narration via the MCP

Tested November 2026 on two lines: timings matched every script word, including
brand names, numbers and URLs, and the pauses fell within 0.1 s of measured silence.

1. `creative_generate_speech` with the script, `voice_id`, model
   `eleven_multilingual_v2` (as `narrate.py`) and `generations_count: 1`; the
   default of 2 takes bills twice. It renders a player for the user. It has no
   speed setting: fit the length with words or pauses, not `--speed`.
2. `creative_transcribe_audio` with the same `flow_id` and
   `connect_from: [<the speech node_id>]`. Linked like this it costs 0 credits
   and times the exact script text. Never transcribe a re-uploaded copy for
   timings: that is blind speech-to-text, billed (~5.5 credits a second), and it
   respells names (a brand such as "Lumio" comes back as "Lumeo",
   "side-by-side" as "side by side"), so `wordStart()` throws.
3. `creative_get_flow_run_status` with each run's `session_ids`: the take's
   `media[0].url` and the transcript's `words_download_url`. Call it even though
   the run's note says a view tracks progress: it is the only way to read the links.
4. Within about 2 hours (the links are signed and expire), run
   `import_mcp_narration.py` with both links. It writes the usual `_vN.mp3`,
   `.words.json` and `.gen.json` and drops punctuation-only "words" such as an
   em dash.
5. The last word's end runs into the trailing silence (by ~0.4 s in testing);
   take the speech end from `speech_end_s` of
   `silence_cuts.py FILE --threshold -35 --min-silence 0.15`, not from that number.

`estimate_only` prices a run but also creates a flow (or node) in the user's
workspace each time, unlike `--dry-run`; reuse that flow and node for the real
run instead of starting fresh. Never paste flow links into project files: they
carry a sign-in token.

## Maintaining the scripts

Python ≥ 3.11, stdlib only. Tests: `uv run --no-project --python 3.12 --with pytest pytest`
from the skill folder; lint with `ruff check scripts`.

When you add or change a rule here, log the incident behind it in `CHANGELOG.md` in
the same commit. Judge the change with the briefs in `evals/` (see its README): they
spend no ElevenLabs credits, but running them costs model time, so ask first.

A rule must hold for any video, not for the one that taught it:

- Word the rule, its examples, the script docstrings, the test fixtures and the
  eval briefs without naming a project, its script, its voices or its characters.
  The project is named in `CHANGELOG.md` only.
- A rule learned from one video is provisional. Mark it "provisional" in the
  CHANGELOG until a video of another kind (a promo, a screen-recording
  walkthrough, a text-only social clip, a character explainer) or an eval of
  another kind shows the same need. Drop or narrow it if that video contradicts it.
- Template code follows the same test: add a helper when two unlike videos needed
  it, not when one did.
