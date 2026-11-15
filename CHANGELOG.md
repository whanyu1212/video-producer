# Changelog

Every SKILL.md rule and the incident that put it there, newest first, with where the
record is. "Origin not recorded" marks rules that were already in the skill when it was
imported and whose incident nobody wrote down; replace it when the story turns up, and
don't guess one. When you add or change a rule, add its incident here in the same commit.

"Provisional" marks a rule learned from one video only. It stays provisional until a
video or an eval of another kind shows the same need (see Maintaining the scripts in
SKILL.md). Every rule dated 2026-11-04 below is provisional unless the 2026-11-12
section confirms it: all of them come from one character explainer, GAD v2.

"GAD v2" is the remake of the GAD (anxiety) explainer in
the private project `gad-explainer-v2`: its `project.md` (Decisions, Versions) and commits
`21d655b` (v1) and `cc2da8f` (v2) hold the evidence cited below.

"LLM intro" is a 30 s text-only motion-graphics explainer (no characters, no footage) in
`~/Movies/video-projects/llm-intro`: its `project.md` (Decisions, Versions) and commits
`28b11a0` and `5d078d2` (tag `v1`) hold the evidence cited below. It is the second
kind of video the skill has made, so it can confirm GAD v2's provisional rules.

"LLM intro 2" is the clean-slate remake of the LLM intro in real 3D ("Glass Pop": frosted
glass tiles with poster type) in `~/Movies/video-projects/llm-intro-2`: its `project.md`
(Decisions, Versions) and commits `99f77b0`, `46781e2` and `57d3a49` (tag `v1`) hold
the evidence cited below. It is the skill's first 3D video. Like the LLM intro it is a
motion-graphics explainer, so it does not count as a video of another kind.

"Peer ADHD" is a 2-minute narrated explainer made by another AI video producer (a
commercial app), not by this skill, in the private project `adhd-explainer`: its
`assets/media_assets.json`, its cut's version history and the app's session log hold the
evidence cited below. It shows what
another producer measured and got wrong, so a rule taken from it stays provisional until
a video made with this skill shows the same need.

"Solar short" is a 59 s 9:16 narrated data explainer drawn as one grid of 100 squares
(no characters, no footage) in `~/Movies/video-projects/solar-caught-up`: its
`project.md` (Decisions, Reviews, Versions) and tag `v1` hold the evidence cited below.
It is the skill's first data-journalism piece and first vertical-first video, so it is a
video of another kind for the rules above.

## 2026-11-15: lessons from the solar short

The first video made with the review, reference and critic setup. It confirmed some of
the morning's rules and contradicted one number.

| Rule (SKILL.md) | Incident | Record |
|---|---|---|
| `narrate.py` read-time range widened to 2.1-2.9 words a second. Provisional | The take read 111 words in 38.96 s, 2.85 a second, outside the 2.1-2.5 the dry run assumed; it came back 13 s shorter than estimated | solar short `public/assets/narration/narration_v1.words.json` |
| MCP narration: no speed setting, so fit the length with words or pauses; Workflow 4: pauses also bring a short take to length. Provisional | `creative_generate_speech` takes no voice settings; the short take reached 59 s through 12 s of pauses at paragraph breaks instead of a paid retake | solar short Decisions |
| `silence_cuts.py` reports `noise_floor_db` and, when it sits within 3 dB of `--threshold`, says to retry 8 dB above it; Workflow 4: cut on the take as generated. Provisional | The take's quietest 5% sat at −58.3 dBFS, so at −60 the cuts landed up to 6 s from the words; −50 put every cut between the right words. The take raised 16 dB had no silence at all. The two LLM intros' takes sit at −90 and −69 | `scripts/tests/test_silence_cuts.py`; solar short `src/timeline.ts` |
| Template captions sit above the bottom 15% on a vertical frame; quality floor: keep what must be read out of that zone on 9:16; critic brief question 5. Provisional | The captions sat in the bottom 8%, under TikTok's and Reels' buttons; neither the measurements nor the critic caught it, I did from the platforms' layout | `template/src/scenes/WordCaptions.tsx`; solar short Reviews |
| Quality floor: a hold where only small things move can still be listed as still; look and name the ones you keep. Provisional | After motes and a breathing glow were added, `probe.py` still listed 15 holds of 0.5-0.7 s: whole-frame change stays under freezedetect's threshold when only particles move | solar short Versions |
| Quality floor: when the primary source cannot be opened, never work around the block; use agreeing reports and say so. Provisional | Ember's pages showed a bot check and a mirrored PDF was refused; the figures rest on four reports that agree | solar short Decisions |
| Critic brief: expect findings from stills caught mid-way. Provisional | The critic's first run gave nine findings: six held and were fixed (a muddy transition, a colour meaning two things, a faint credit, a flat ending, a missing count-up, an ambiguous "+30%"), three came from stills caught mid-line or mid-fade and were rejected | solar short Reviews |

Confirmed on a video of another kind (no longer provisional, for this kind of evidence):
the export's mode report (it went dynamic again, peaks 5.0 dB over; `--limit` took 6.0
dB, still not heard), the scene lint (no findings on the short's six files) and the
settle check (`last_change` 0.06 on a still ending).

## 2026-11-15: lessons from another video producer, and taste from outside the maker

Reading how another AI video producer made its ADHD explainer turned up checks this skill states but never
measured, and one export defect that every video made with this skill already had.

| Rule (SKILL.md) | Incident | Record |
|---|---|---|
| Workflow 10 and `loudnorm_export.py`: report the mode loudnorm ran and its cause, and check the export's own peak and loudness. Not provisional: measured on every render the skill has made | loudnorm falls back to dynamic mode when one gain would push peaks over the ceiling or the range is wider than the target, and the script never said so. Every render this skill has delivered went dynamic: LLM intro v1 (peaks 4.6 dB over, range 13.8 LU), LLM intro 2 v1 and v2 (1.0 and 1.2 dB over; both still landed on target). Peer ADHD's narration (−23.9 LUFS, −0.44 dBTP) came out at −15.4 LUFS and −0.7 dBTP, missing both targets without a warning | `scripts/tests/test_loudnorm_export.py`; LLM intro and LLM intro 2 `out/` renders |
| Workflow 10: `--limit` (one gain plus a peak limiter) when the warning is about peaks; tell the user how many dB it took off and that nobody has heard it. The 2 dB overshoot allowed without a warning is set from the two LLM intro 2 renders. Provisional | `level_take.py` did not make linear mode possible (its make-up gain restores the peaks). `--limit` on Peer ADHD's narration: −14.1 LUFS, −1.4 dBTP, 13.5 dB off the peaks; on LLM intro v1 with its picture: −14.1 LUFS, −1.4 dBTP, 5.1 dB, picture copied untouched. Neither has been listened to | `scripts/tests/test_loudnorm_export.py` |
| Workflow 3: fit the script to the length with `narrate.py --dry-run --target-seconds` before paying. Provisional | Peer ADHD paid for a second narration only to change its length: 135.7 s at speed 1.0, then 122.2 s at 1.1, for "about 2 minutes". The rate range comes from three takes by three voices: 2.11 (Peer ADHD), 2.13 (LLM intro 2) and 2.53 (LLM intro) words a second | Peer ADHD `media_assets.json`; both LLM intros' `.words.json` |
| Remotion rules: `lint_scenes.py`. Its errors restate rules already here; the `html-media` and `frame-literal` warnings are new. Warnings provisional | The other producer refuses scene code like this at render time. Its check misread props named `start` and `endAt` as footage trims, so this one matches code that does the thing, not names. Zero findings on 59 files: the template, the re-voice eval, both LLM intros and Peer ADHD's scene | `scripts/tests/test_lint_scenes.py` |
| Quality floor: the last frame settled, now measured by `probe.py` (`last_change` at a fixed 30 fps, threshold 0.8). Threshold provisional | The rule had no measurement. The other producer's render check flagged two Peer ADHD sections as ending mid-move; they measure 1.53 and 1.79 here, and a third that ends on a fade-out 1.05. Both LLM intros end on deliberate drift, a pulsing glow and dust at 0.44 and 0.14 | `scripts/tests/test_probe.py` |
| Quality floor: facts include spoken claims; for health, money or legal subjects, sources in `project.md` and a decision on a not-advice line. Provisional | The rule covered on-screen text only. Peer ADHD's review asked a second model for factual errors in the narration as well, and its end card carries a not-medical-advice line | Peer ADHD session log |
| Workflow 3, 8 and Iterating 1; `review/taste.md`; `references/library.json` and `refs.py`; template References and Reviews sections. Provisional: no video has been made with them yet | The user asked how taste is assured and who reviews. Measurements hold only the floor, and the other producer has a second model review every draft because the maker cannot judge its own work fairly. The library (98 entries, 21 genres) came from four research passes that checked links but watched no videos. Frames stay outside the repo because they are other people's work | `review/taste.md`; `references/library.json` |

## 2026-11-12: review tools for what the two LLM intros left open

A look back over both LLM intros listed what the skill still left to hand work or to a
reviewer. All provisional: the two are the same kind of video. The template field is the
exception, since GAD v2 wired its ducking the same way.

| Rule (SKILL.md) | Incident | Record |
|---|---|---|
| Template `music.duckThrough`; quality floor: set it above the longest gap between words the music should stay down through | Gaps between words over 0.4 s release the duck, and a gap is the take's own silence plus the inserted pause: 0.72 s after the hook line and 1.55 s before the fourth line on LLM intro 2. The music rose in each one, the suspense pause before the payoff included. GAD v2 built its spans the same way. In a scratch render the music band in a 0.6 s pause measured −31.7 dB without the option (−30.1 with no duck) and −42.3 dB with `duckThrough: 0.8` | `template/src/Video.tsx`; LLM intro 2 `src/timeline.ts` pauses |
| `probe.py --timeline`; Workflow 4 and 8: check a take and a render for an uneven spread, and report that sound was checked on meters only | Both LLM intros were delivered with nobody having heard them. The per-second printout was typed by hand four times to find loud openings and uneven takes. LLM intro 2's take spans 6.6 LU and its render 7.4 LU | LLM intro 2 `narration_v1.mp3`, `out/v1.mp4` |
| `level_take.py` for a take that `--timeline` flags; opt-in | LLM intro 2's take reads 13 LUFS in one sentence and 19 in the last. A 2:1 compressor narrows 6.6 LU to 3.4 with the pause cuts still in silence. `dynaudnorm` barely moved it (6 to 5 LU), and `compand` at its default start level turned the opening line down 3.6 dB, hence `volume=-20`. Nobody has listened to the result | measured on LLM intro 2 `narration_v1.mp3` |
| `cut_frames.py` replaces the hand-written ffmpeg line in Workflow 8; each row leads with the frame before the cut | The select expression was typed by hand three times on LLM intro 2, once with a wrong flag, and with frame numbers one late for two of five cuts (the template cuts at round(seconds × fps)), so the true first frame of those beats was never looked at | 2026-11-12 "3D and cut checks" below |
| `frame_diff.py` replaces the hand-made still-versus-render comparison (3D section) | A whole-frame mean was used on LLM intro 2; it would miss one changed object, so the script reports the worst of 16×9 blocks (a 2% box 60 levels brighter: mean under 3, worst block over 12). Video compression alone gives about 5. Run on LLM intro 2 at `46781e2`, before the lighting fix, it reports mean 3.4 and worst block 30.2 | `scripts/tests/test_review_tools.py`; LLM intro 2 commit `46781e2` |
| `loudnorm_export.py --replace`, for an export nobody was sent; Workflow 10 | On both LLM intros the delivery file was exported, a later review found a fault, and the file was deleted by hand to export again. Both are the same kind of video, so provisional | LLM intro session; LLM intro 2 commit `57d3a49` |
| `import_mcp_music.py` warns on a true peak above 0 dBTP | LLM intro 2's bed arrived at +0.5 dBTP and the import printed no warning | LLM intro 2 `music_v1.gen.json` |
| Quality floor: facts on screen are checked or plainly illustrative, recorded and told to the user | LLM intro showed token IDs and a 15-trillion-word figure from memory; LLM intro 2 a "62%" with invented candidates. Both were flagged to the user only in chat. Both are the same kind of video, so provisional | both `project.md` Decisions |
| Iterating 1: take mock-up compositions out of `Root.tsx` once a look is chosen | LLM intro 2 shipped v1 with four mock-up compositions still registered | LLM intro 2 `src/Root.tsx` |
| 3D: frame each shape on its own; check `Vertical` stills | Three `Vertical` stills of LLM intro 2: the HTML slabs reflow, the 3D scene keeps its vertical field of view and loses both sides (the sentence shows two of six tiles) | LLM intro 2 `out/vert_*.png` |

Checked, with no rule change:
- `music_beats.py` was suspected of being too strict on LLM intro 2's bed. Split into bands
  it reads 118.1, 119.0 and 119.7 BPM with first beats 0.37 to 0.49 s: grids that drift
  0.4 s apart over 30 s, so no one grid is supported. The refusal stands. It also refuses
  both narration takes (confidence about 1.2, support about 0.5) and irregular bursts.
- Tests now run scripts in the test process, not a subprocess, so coverage tools see
  their lines. Coverage would not have caught either review finding on PR #2; the
  adversarial cases in `test_review_tools.py` are the answer to that.
- Hold time of a payoff stays a rule (2026-11-12 below): a generic checker would need to
  know when each scene starts to leave.

## 2026-11-12: 3D and cut checks from LLM intro 2

All provisional: one video, and the first one in 3D.

| Rule (SKILL.md) | Incident | Record |
|---|---|---|
| 3D: mock with CSS perspective first; install `@remotion/three`, `three`, `@react-three/fiber` 8 and `@types/three` pinned, only with the user's OK; `angle` GL renderer | The user picked a 3D look from CSS mock-ups and approved the packages; the docs require `angle` for rendering three.js | LLM intro 2 `package.json`, `remotion.config.ts`; project.md Decisions |
| 3D: set a moving camera inside the canvas every render | Every dolly, push-in and tracking move was silently ignored: the chain-of-tiles beat looked down the row from its first position instead of following it. The contact sheet showed it | LLM intro 2 `src/three/kit.tsx` `CameraRig` |
| 3D: everything a frame needs exists at the first draw; hold the render for fonts and mount | A reflection environment set in `useEffect` reached only frames after a stage's first draw, so every still showed shaded lilac glass and the render a washed-out white. Text textures drawn before the canvas had mounted were missing from the first stills | LLM intro 2 `src/three/kit.tsx` `StudioLight`, `Stage`; commit `57d3a49` |
| 3D: compare a still of frame N with frame N of the render | After the fix the two differ by a mean of 0.4-1.0 levels in 255 in three beats; before it they differed visibly, and only a reviewer comparing stills against render frames noticed | LLM intro 2 project.md Decisions |
| 3D: `flat`, cached canvas textures checked at 480 px, opaque instanced meshes, timed draft | Tone mapping greyed the white glass; the floor sentence of the next-token beat was under the 54 px floor at 480 px until the stage was scaled 1.17× and tilted up; a wall of about 480 tiles is one opaque instanced mesh; the full 30 s rendered in about 25 s | LLM intro 2 `src/scenes/Predict.tsx`, `src/scenes/Scale.tsx` |
| Workflow 8 and quality floor: tile the first frames after each cut; every beat opens on content | Four beats opened on 3-13 frames of empty backdrop (up to 0.43 s before the title's first slab). `probe.py` and the 19-frame contact sheet both passed it; a tile of the first four frames after each cut showed it | LLM intro 2 project.md Decisions; commit `57d3a49` |

Also seen on LLM intro 2, with no rule change:
- `pauses` in the template played the take in seven slices with no hand-written slicing; the template's second user.
- The quiet-take warning stayed silent on a −15.9 LUFS take, as it should.
- `music_beats.py` refused a grid on a bed prompted at 120 BPM (confidence 1.2, support 0.71). Whether that bed's beat is really weak was not checked by ear.

## 2026-11-12: gaps found making the LLM intro

Everything below was done by hand, with throwaway code or by luck on the LLM intro, and
is now a script, template code or a rule.

| Rule (SKILL.md) | Incident | Record |
|---|---|---|
| Template: `pauses` on the narration play the take as slices; `effects` is one list played by `Video.tsx`; music takes `fadeIn` / `fadeOut`; `timeline.ts` exports `words` on the video timeline and `cue()` | Both videos wrote all three by hand: GAD v2 as `PAUSES`, `SFX` and `MUSIC.fadeIn/fadeOut`, the LLM intro as `cuts`, `effects` and `fadeOutSeconds`. Two unlike videos, so it is template code. Checked in a scratch project: with a 1 s pause after 1.2 s of a 0.5 s-lead take, the render is silent 1.4-3.0 s and the caption after the pause highlights its word | GAD v2 `src/timeline.ts`; LLM intro `src/timeline.ts`, `src/Video.tsx` |
| Both narration routes print the take's loudness and warn below −24 LUFS; note it in Decisions before setting music and effect levels | The LLM intro's MCP take measured −34 LUFS and nothing said so; music and effects were set against it only after the first render. GAD v2's takes measured −27.7 and −18.8 | LLM intro `project.md` Decisions; GAD v2 `project.md` |
| `probe.py` checks black stretches frame by frame (10 a second): runs at least 0.2% lit go under `dark` without a warning, empty runs still warn. Provisional | blackdetect flagged 6.03-6.63 s (a sentence on a near-black backdrop, 0.8% lit) and 11.47-11.73 s (a counter, 0.44-0.7% lit); both were explained to the user by hand. The backdrop's own dust motes light about 0.01-0.05%. Review on PR #2: judging a stretch by its middle frame clears empty frames on either side of a caption, so runs are split; on the LLM intro that leaves one real 0.1 s near-empty handoff at 6.03 s | LLM intro `project.md` Decisions; `scripts/tests/test_probe.py` |
| `synth_sfx.py`: free ffmpeg effects (tick, blip, chime, whoosh, impact, riser, swell) gained to a measured −3 dBTP. Provisional | "Prefer free effects" had no free source. The LLM intro synthesized seven effects in a shell script; a 0.89 limiter still let one reach +1.1 dBTP, and unseeded noise gave a different file every run | LLM intro `make_sfx.sh` |
| `import_mcp_music.py`, and the MCP music steps: schema first, `generations_count: 1` (music defaults to 4 variations). Provisional | The LLM intro's bed was downloaded with curl and its `.gen.json` written by hand. `creative_generate_in_flow` takes no model parameters, so the node was added and run separately | LLM intro `public/assets/music/music_v1.gen.json` |
| `music_beats.py`: tempo, beat grid and nearest beat to a planned cut; no grid below 2× chance or when under half the beats have an onset of their own (at least 0.5 dB). Provisional | The cut-on-the-beat rule (2026-11-11) had no script. On the LLM intro bed, prompted at 110 BPM, it finds 109.8 BPM at confidence 2.1 with every beat supported, and the kick band is loudest on its beats (6,907 against about 5,200 half a beat or 100 ms off). Review on PR #2: a steady tone with one fade-in scored confidence 8 from its single attack; the support check rejects it (its jitter rises 0.005 dB, the bed's quietest beat 0.7 dB). Only one real bed tested | `scripts/tests/test_music_beats.py`; measured on LLM intro `music_v1.mp3` |
| Workflow 8: for each beat's payoff, work out from the source how long it holds before its scene leaves. Provisional | "mat" snapping into the blank, the next-token beat's payoff, was solid for 0.76 s, under the 1.2 s floor. Stills and the contact sheet all looked right; a review of the timing in the source caught it. The fix was a 1.2 s pause after "next one." (1.56 s) | LLM intro commit `5d078d2` |
| Workflow 10: export only once the review passes. Provisional | `loudnorm_export.py` refused to overwrite the first export; its message was hidden in a pipe, and the frames of the stale file were read as the fix's | LLM intro session, before commit `5d078d2` |

Confirmed by the LLM intro, so no longer provisional (rules from 2026-11-04):

| Rule | Evidence on the LLM intro |
|---|---|
| A cue on a word spoken twice needs `nth` (`check_cues.py`) | `cue('one', 1)` for the payoff and `cue('internet', 1)` for the outro; "one" is spoken three times |
| Cut only where `silence_cuts.py` finds silence; add pace with pauses, not retakes | Pauses after "model." (cut 4.22 s) and "next one." (8.87 s) filled 30 s without a retake |
| Speech end from `silence_cuts.py --threshold -35`, not the last word's `end` | 23.42 s against the last word's 24.10 s |
| Narrate through the MCP with `generations_count: 1`, transcribe linked to the speech node, read links with `creative_get_flow_run_status` | 61 of 61 words timed, 0 credits for the transcript, 347 for the take |

## 2026-11-11: motion, text-size and sound rules borrowed from two public skills

The skill had measurement rules but almost nothing on how things should move. These come
from reading `Tejashmakwana/motionmaxxing` and `Vincentwei1021/video-shotcraft` (both
Apache-2.0): numbers and methods only, reworded, no text or code. None has been tried on
a video made with this skill, so all are provisional.

| Rule (SKILL.md) | Incident | Record |
|---|---|---|
| Motion defaults, length: arrivals about 0.4 s, a fade about 0.2 s, exits 0.3-0.5 s; under 0.2 s or over 0.8 s is a choice. Provisional | motionmaxxing's medians at 30 fps: entries 12 frames, opacity 6, exits 10-14, with 6 and 24 frames as the quartile edges. Its sample is about 50 moments of 3-7 s from SaaS launch films, decoded by models with one human rater | motionmaxxing `references/motion.md` R1.1; `docs/KNOWN-LIMITS.md` |
| Motion defaults, easing: arrivals ease out, exits ease in, nothing linear. Provisional | Same sample: 58% of landings ease out, 37% of exits ease in. video-shotcraft bans linear motion from one user's feedback | motionmaxxing `references/motion.md` R1.4-R1.5; video-shotcraft `references/aesthetic-rules.md` R2 |
| Motion defaults, overshoot: at most one, under 10%, late. Provisional | Same sample: overshoot on under 9% of moves, peaking about +8% late in the move | motionmaxxing `references/motion.md` R1.10-R1.11 |
| Motion defaults, entrances move; opacity is a helper. Provisional | Same sample: 3,392 transform entries against 584 opacity fades | motionmaxxing `references/motion.md` R1.6 |
| Quality floor, text: read text at least 5% of the short side (54 px at 1080), secondary 3% (32 px), checked at 480 px wide. Provisional | video-shotcraft sets 56 px and 32 px at 1080p from one user's feedback. 5% is used here because the template's captions are 5% (54 px); the 2 px gap was not tested | video-shotcraft `references/aesthetic-rules.md` Q11 |
| Quality floor, cuts: a cut meant for a music beat lands within 0.1 s. Provisional | video-shotcraft measures cuts against a fitted beat grid and passes at 3 frames or less; it reports one 70 s film with every cut within 2.2 frames. When this rule was added the skill had no beat-detection script; `music_beats.py` (2026-11-12) now measures the grid, with the music plan's section starts as the fallback when the beat is weak | video-shotcraft `references/music-beat-sync.md` §5b |
| Workflow 5 and quality floor, sound: effects in one commented list; a file whose true peak is below −12 dB is replaced or boosted. Provisional | video-shotcraft keeps effects in one table and requires sources peaking below −12 dB to be replaced or boosted, then checked in the render, not the preview | video-shotcraft `references/sound-design.md` §4; `references/final-review.md` A5-A6 |

Not taken, and why: motionmaxxing's shorter reading times (0.2 s per word, no minimum)
and its "end mid-motion" contradict this skill's text and settled-last-frame rules; its
bans on crossfades, corner labels and left-aligned headlines and video-shotcraft's energy
arc and mood presets are one author's taste or one film, and only fit promos.

## 2026-11-11: rules must not depend on one video

The user asked that tuning the skill not be tied to the GAD explainer. At that point 23
changelog lines cited it, SKILL.md's examples used its words and voices, one quality-floor
rule only fitted cartoon characters, and one of the three evals was a cut-down copy of it.

| Rule (SKILL.md) | Incident | Record |
|---|---|---|
| Maintaining: word rules, examples, fixtures and eval briefs without naming a project; a rule from one video is provisional until another kind of video or eval confirms it; template code needs two unlike videos | Every rule added on 2026-11-04 was justified by one project, and nothing checked it against another kind of video | This file, 2026-11-04 sections |
| Quality floor, drawn figures, icons and diagrams: parts that belong together touch, nothing floats or is cut off, colours stand out (was "Characters": head, hair, hands). Provisional | The wording only fitted a cartoon person; the defect behind it (parts drawn apart, colour lost on a background) is not specific to one | 2026-11-04 "Characters" row below |
| Examples in SKILL.md, script docstrings and test fixtures use neutral words | They quoted the GAD script, its voices and a product name | `git diff` of this commit |
| `evals/`: `revoice-existing-cut` re-skinned (same word counts, so the graders' numbers stand); new `walkthrough-scenes-from-recording` covers scene-building on footage | No eval built scenes, and one of three shared the GAD script's subject | `evals/README.md` |

## 2026-11-11: precedence over the official Remotion skills

The `remotion-dev/skills` set (13 skills, version 4.0.542) was installed globally to
cover component APIs this skill only touches on. Read as installed, it contradicts
this skill in six places, so an agent loading both would get two sets of instructions.
No video has been made with both loaded yet, so the rule is preventive and provisional.
The `walkthrough-scenes-from-recording` eval added the same day is the first that builds
scenes and can test it.

| Rule (SKILL.md) | Incident | Record |
|---|---|---|
| With the official Remotion skills: use them for component APIs; this skill wins on new projects, rendering, voice-over, length, captions, and sound and footage components. Provisional | `remotion-best-practices` says "Only render if the user is very explicit"; `remotion-create` scaffolds with `create-video`; `voiceover.md` calls ElevenLabs per scene with no word times and sizes the video with `calculateMetadata`; `remotion-captions` requires `Caption` (`startMs`, `endMs`); `audio.md` and `embedding-videos.md` import from `@remotion/media` and show `volume` only as a number or an `interpolate()` value, while `duck.ts` passes a function of the frame | `~/.claude/skills/remotion-*` as installed 2026-11-11 |

## 2026-11-04: scripts for iterating with the user

The re-voice and mock-up steps added the same day were done by hand or with throwaway
scripts in GAD v2. Each now has a tested script that replaces the prose describing the
manual steps.

| Rule (SKILL.md) | Incident | Record |
|---|---|---|
| Tile mock-ups with `mockup_sheet.py`; the PNG holds no text, so each mock-up draws its own name, and the HTML labels stills and carries voice clips | The A/B/C character sheet and the voice and character options page were built with one-off `tile.py` and `build_options.py`. This ffmpeg has no `drawtext`, so the option names were drawn inside the `MockupSheet` composition | GAD v2 `src/mockups/MockupSheet.tsx`, `out/mockups/options.html` |
| Run `check_cues.py`; a cue on a word spoken twice needs `nth` | "when" is first spoken in "even when everything seems fine", so the title has to use `cue('When', 1)`. v1's Versions row records an "early title wipe" fixed in render 4. On the v2 project the script flags eight other cue calls that take the first of a repeated word ("health", "And", "Anxiety", "most") for a check | GAD v2 `src/timeline.ts`, `project.md` Versions (v1) |
| Cut only where `silence_cuts.py` finds silence, measured as RMS over 50 ms at or below −60 dBFS | `ffmpeg silencedetect` at −60 dB finds no silence at all in the v2 take: it judges single samples, and the mp3's noise floor sits around −50 to −60 dB. So the "≤ −60 dBFS" rule could not be checked with the command it implied. With 50 ms RMS, the span midpoints fall within 0.025 s of all seven cuts chosen by hand | GAD v2 `src/timeline.ts` `PAUSES`; the measurements are in commit `b85f428` |
| Speech end from `silence_cuts.py --threshold -35` (Narration via the MCP, step 5) | The same script replaces the raw `silencedetect` line: 61.65 s against silencedetect's 61.69 s on the v2 take | GAD v2 `src/timeline.ts` `SPEECH_END` |
| Match levels with `match_levels.py` | Claire's take measured −27.7 LUFS and Bree's −18.8 (8.9 LU apart). Music went from −9 to −18 dB and effects from 0.09 and 0.9 to 0.032 and 0.32, all set by hand; the script reproduces them (−17.9 dB, 0.0323, 0.323) | GAD v2 `src/timeline.ts` `MUSIC`, `SFX` |
| `evals/`: three briefs that spend no credits | So that SKILL.md edits like the ones above can be judged before they ship | `evals/README.md` |

## 2026-11-04: iterating with the user, character check (`41ad786`)

Learned in GAD v2, where the user disliked v1's character and voice.

| Rule (SKILL.md) | Incident | Record |
|---|---|---|
| Show options before a redesign: 2-3 mock-up compositions of the same moment, plus free voice previews | The user found v1's figure fake. Three directions (Soft & grounded, Rounded minimal, Storybook) were rendered as `MockupA/B/C` stills and the user picked Rounded minimal. Claire was picked from the free previews of five voices | GAD v2 `project.md` Look, Decisions; `src/mockups/` |
| Price the round and wait for the go-ahead | Re-voicing cost 916 credits, as much as v1's take; the previews cost 0 | GAD v2 `project.md` Budget |
| Re-voicing: generate the next `_vN` take and keep the old one | Bree's `narration_v1` was kept next to Claire's `narration_v2` | GAD v2 `src/timeline.ts` |
| Re-time everything from the new word list | Every beat start moved: the cues are words, not seconds, so they re-timed themselves once the words file changed | GAD v2 commit `cc2da8f` |
| Add pace with silence: slices cut in measured silence, pauses at paragraph breaks | v1 played the take in 3 slices cut at −40 dB. v2 plays it in 8, with 0.35-0.5 s pauses at the paragraph breaks, cut at ≤ −60 dBFS. Why the threshold changed was not recorded | GAD v2 `git diff 21d655b cc2da8f -- src/timeline.ts` |
| Re-fit the music with `atempo` (old ÷ new length, within about ±8 %) | The bed was slowed with `atempo=0.89846` for v1 (73.5 s) and `0.92361` for v2 (71.5 s), and "The good news?" still lands on its brighter section | GAD v2 `project.md` Decisions |
| Match levels | Claire's take is about 9 dB quieter than Bree's; music and effects were moved 9 dB down to keep the balance | GAD v2 `project.md` Decisions |
| Feedback during a render: reproduce on a still, fix, show the still, re-render; check every other character, pose and shape | After review, v2's head floated above the body and the hair sat wrong. The head was seated on a neck and collar, and the hair redrawn as a cap over the crown | GAD v2 `project.md` Versions (v2); commit `41ad786` message |
| Quality floor, Characters: zoom in on full-size stills; head joins body, hair on the skull, hands meet arms, colours stand out on every background; a contact sheet is too small | The floating head and misplaced hair slipped past the contact sheet. Mo's sage top vanished on the teal breathing circle and the mint symptom beat, so it became violet #9D8FE2 | Commit `41ad786` message; GAD v2 `project.md` Look |
| Close the round as a new version, with the request and the changes in Decisions | v2 was committed, tagged and logged as its own version | GAD v2 `project.md` Versions |

## 2026-11-03: narration via the MCP (before the import)

Tested on two short lines on a machine with no ElevenLabs API key. Records: the MCP test
folder of that session (`narration_v1`, `stress_v1` and `blind_v1` word files, `check.mjs`)
and the SKILL.md backups taken before and after.

| Rule (SKILL.md) | Incident | Record |
|---|---|---|
| Narrate through the MCP when there is no key, saved with `import_mcp_narration.py` | No API key on the machine; the GAD v1 and v2 takes were both made this way | GAD v2 `project.md` Decisions |
| `generations_count: 1` | The default of 2 takes bills twice; recorded in the rule only | SKILL.md |
| Transcribe linked to the speech node (free, exact text), never a re-uploaded copy | The blind transcript of a re-upload respelled a product name and "side-by-side" as "side by side", so `wordStart()` threw; it is also billed per second | `blind_v1.words.json` compared with its script |
| Read the links with `creative_get_flow_run_status` and import them within about 2 hours | The run's note says a view tracks progress, but only `creative_get_flow_run_status` returns the links, and they are signed and expire | Recorded in the rule only |
| Drop punctuation-only "words" | The transcript timed an em dash as a word | `scripts/tests/test_parsing.py` fixture |
| Take the speech end from measured silence, not the last word's `end` | The last word's end ran about 0.4 s into the trailing silence | Recorded in the rule only |
| `estimate_only` creates a flow each time; never paste flow links into project files | Pricing a run left flows in the workspace, and the links carry a sign-in token | Recorded in the rule only |
| Music plans, seeded retakes and effects come from the scripts | The MCP's music takes one prompt and a total length (no timed sections), and its speech has no seed | Recorded in the rule only |

## Present at import (`59c45cc`), origin not recorded

These rules predate this repository. Where GAD v2's review of the original cut (made with another tool)
later caught the defect a rule describes, that's noted as a confirmation, not as the rule's origin.

| Section | Rules | Later confirmation |
|---|---|---|
| Workflow 1-3 | Quote the brief; probe and contact-sheet sources before planning; plan, `--dry-run`, never spend credits without the go-ahead | — |
| Workflow 4 | Voice first; `DURATION_SECONDS` from the measured speech end | — |
| Workflow 5-6 | Music as timed plan chunks; scenes time animation from `wordStart`, not typed seconds | The original's cues were typed seconds, so any narration change meant re-timing by hand (GAD v2 `project.md`, "What v2 fixes") |
| Workflow 7-10 | Stills before renders; review every render; commit and tag each cut; deliver with `loudnorm_export.py`; other shapes from the same scenes; thumbnail at 170 px | — |
| Quality floor | Fix every tool warning; no still stretch over 0.5 s; animation settles; text timing and safe margin; cuts on measured times; speech above music; footage crops and personal data | The original had three still stretches flagged by `probe.py` (11.95, 58.8, 64.6 s) and a symptom card on screen for about 1 s (GAD v2 `project.md`, "What v2 fixes") |
| Remotion rules | Frame-driven animation only; `staticFile` assets; timeline wiring; typecheck; licence note | — |
| Costs and keys | Credit rates, `--dry-run`, key from env or Keychain and never printed | — |
