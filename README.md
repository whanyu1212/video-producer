# video-producer

A Claude Code skill that produces short videos end to end: product promos, explainers,
social clips, narrated walkthroughs of screen recordings, thumbnails. Claude plans the
piece, writes the scenes as React code, generates narration, music and sound effects,
renders, measures the result and reviews its own frames before delivering.

- **Remotion** is the timeline: scenes are React components timed in frames.
- **ffmpeg** measures and delivers: loudness, still and black frames, contact sheets.
- **ElevenLabs** makes the voice, music and effects, through its API or its MCP connector.

[SKILL.md](SKILL.md) is the skill itself: the workflow, the quality floor and the
command table. This README covers installing, the layout and maintenance.

## What a run looks like

1. You ask for a video ("a 30 second explainer about X").
2. Claude writes the brief, look, script and beat plan to `project.md`, and stops with a
   credit estimate. Nothing is spent without your go-ahead.
3. Narration comes first; every animation is then timed to the spoken words.
4. Claude builds the scenes, checks stills, renders, and reviews the render: warnings
   from `probe.py`, a contact sheet, the first frames after each cut, text size at
   phone width.
5. The delivered cut is loudness-normalised (−14 LUFS by default), committed and tagged
   in the video's own project folder.

When you dislike a look or a voice, Claude mocks up options side by side before
rebuilding anything.

## Requirements

| Need | Notes |
|---|---|
| Claude Code | The skill loads from `~/.claude/skills/` |
| Python ≥ 3.11 | The scripts use the standard library only |
| ffmpeg and ffprobe | Text drawing (`drawtext`) is not needed; the evals also need `libmp3lame` |
| Node.js and npm | For Remotion; the first render downloads a headless browser |
| ElevenLabs account | Optional. Without it, videos have no generated voice or music |

ElevenLabs works two ways:

- **API key**, read from `ELEVENLABS_API_KEY` or, on macOS, from the Keychain item
  `elevenlabs-api-key`. Needed for timed music plans, seeded retakes and generated effects.
- **MCP connector** (OAuth, no key): voice browsing, narration and one-prompt music.

Sound effects for UI-style motion (`synth_sfx.py`) are made with ffmpeg and cost nothing.

Remotion is free for individuals and companies of up to 3 people; larger companies
need a Remotion company licence.

## Install

Clone the repository and link it into Claude Code's skills folder:

```bash
git clone https://github.com/whanyu1212/video-producer.git ~/video-producer
```

```bash
ln -s ~/video-producer ~/.claude/skills/video-producer
```

The link means the checked-out branch is the live skill: switching branches changes
what Claude follows in the next session.

For Remotion's component APIs, the official skills are worth installing alongside
(`npx skills add remotion-dev/skills -g`). Where they disagree with this skill,
SKILL.md says which wins.

## Use

Ask Claude Code for a video; the skill triggers on requests to make, edit, re-cut or
re-render one. New projects are created in `~/Movies/video-projects/NAME` (pass
`--parent` to `new_project.py` for another place), each with its own git history.

The scripts also run on their own. Each takes `--help`:

```bash
python3 ~/.claude/skills/video-producer/scripts/probe.py --help
```

The full list is the command table at the top of [SKILL.md](SKILL.md).

## Layout

| Path | What it holds |
|---|---|
| `SKILL.md` | The skill: workflow, quality floor, motion defaults, Remotion and 3D rules, costs |
| `CHANGELOG.md` | Every rule and the incident that put it there, with where the record is (the cited video projects are the maintainer's own and not published) |
| `scripts/` | Python tools: project setup, measurement, review, narration, music, effects |
| `scripts/tests/` | pytest suite for the scripts |
| `template/` | The Remotion project that `new_project.py` copies: soundtrack wiring, captions, both shapes |
| `references/library.json` | Admired work across 21 genres to pick a project's references from (`scripts/refs.py`); frames and study notes live outside the repo, in `~/Movies/video-projects/_references/` |
| `review/taste.md` | Picking references, studying them, the critic pass and the house style |
| `evals/` | Four briefs for judging a change to SKILL.md; see [evals/README.md](evals/README.md) |

## Develop

Run the tests and the linter from the repository root:

```bash
uv run --no-project --python 3.12 --with pytest pytest
```

```bash
uvx ruff check scripts
```

The tests synthesize their media with ffmpeg and spend no credits. Template changes
are checked by creating a scratch project with `new_project.py`, running
`npm run typecheck` in it and rendering a few seconds.

Changing a rule in SKILL.md comes with three duties (SKILL.md, "Maintaining the scripts"):

- Log the incident behind it in `CHANGELOG.md` in the same commit.
- Word it for any video: no project names, scripts or voices outside the CHANGELOG.
- Mark it provisional until a video of another kind, or an eval, shows the same need.

The evals are billed model runs (not ElevenLabs credits), so they are run on request.

## Status

Early. The skill has made a handful of videos of four kinds (a character explainer, two
motion-graphics intros, a vertical data explainer), and many of its rules are still marked
provisional in `CHANGELOG.md` until a video of another kind confirms them. The reference
library's links were checked, but its videos were not all watched; judge an entry before
adopting it.

## Licence

MIT; see [LICENSE](LICENSE). The reference library links to other people's work and
describes it in its own words: the works themselves belong to their makers. Remotion,
ElevenLabs and the fonts a project loads have their own terms.
