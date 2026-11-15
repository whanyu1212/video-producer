# Taste: references, the critic, the house style

Measurements hold the quality floor; they cannot tell good from merely correct. These
four steps bring in judgement from outside the one model making the video: the user's,
work the user admires, and a reviewer that did not make the cut. Use them for any piece
with a look to decide. Skip them for a trim, a re-voice or a format change.

`V=~/.claude/skills/video-producer/scripts`. `refs.py` keeps frames, notes and the house
style under `~/Movies/video-projects/_references/` (`--root` to change it), outside the
skill, because frames of other people's work must never be committed.

## 1. Pick references at the brief

1. Read the house style: `python3 $V/refs.py house` prints its path.
2. `python3 $V/refs.py genres`, then `python3 $V/refs.py list --genre XX` for the piece's
   genre (and a neighbouring one if the piece mixes two). List one genre at a time; never
   read the whole library into the conversation.
3. Offer the user 4-6 candidates, a line each, and let them pick 3-5. References the user
   brings come first; add one to `references/library.json` (the next number in its genre)
   only if they want it kept.
4. Record the picks in `project.md` under References: ID, title, what this piece takes from it.

## 2. Study each pick once

`python3 $V/refs.py show ID`: when it is studied, read its notes and move on. When not,
`python3 $V/refs.py study ID` starts its notes and prints how to make its frame sheet.

- Frames need a file. A clip the user supplies (a download they made, a screen recording)
  becomes a sheet: six frames at the moments that matter (the opening, a dense
  explanation, a transition, the payoff, the last frame). Browser screenshots reach only
  this conversation, not a file, so without a clip write notes only.
- Downloading a video from YouTube or another site needs the user's OK and may break the
  site's terms: ask, never assume.
- Notes are in your own words, under about 150 words, with no quotes from the work. A frame
  sheet is never used in a video.
- Cost: a sheet is one image the first time; later projects read only the notes.

## 3. The critic pass

Run it once per round, on the first full render whose own review (Workflow step 8) passes,
and again after a redesign. Spawn a subagent that did not make the cut, on a smaller
model where it gives specific answers. Give it the brief, the references and the frames,
and nothing that carries your view of the cut: no scene code, no plan reasoning, no
"I think this works".

Make a combined reference sheet first when the picks have sheets:
`mockup_sheet.py <root>/E2-01/sheet.png="E2-01" ... --cols 2 --out out/review/refs`.

The brief, filled in:

```
You are reviewing a draft video against its brief and the work it is meant to stand next
to. You did not make it; say what a demanding creative director would say.

Brief: <About, Brief and Look from project.md>
Script: <the narration, when there is one>
References: <for each pick: ID, title, its notes>. Their frames: <out/review/refs.png>
The draft: contact sheet <path> (a cell every N s, left to right, row by row); cut frames
<path> (each row: the last frame before a cut, then the first frames after it).

1. Against the references: where does the draft fall short? Name the three weakest
   moments with their times and what a top studio would do there instead.
2. Defects: each with its time, what is wrong and the smallest fix. Keep definite defects
   apart from matters of taste.
3. Coherence: one palette, type and motion language throughout? Does the ending answer
   the opening?
4. Claims (informational pieces): every fact a viewer would take as true, spoken or on
   screen, with its time; mark any that look wrong, outdated or overstated.
5. The platform: anything that must be read in an area the platform covers with its own
   buttons and text (on 9:16, the bottom 15% and the right edge)?

Be specific. Say what you cannot judge from stills (sound, speed of motion).
```

A still frame shows a caption line part-way through, and a stagger or a fade mid-way:
expect findings about cut-off captions, faint text or a half-built shape, and check them
against the moments either side before acting.

Then check every finding yourself, on frames or measurements, before changing anything:
the critic's times are estimates and its claims can be wrong. Fix what holds, and record
each finding in `project.md` under Reviews (finding, evidence, fixed or rejected and why).
Rejected findings stay recorded, so a later round does not redo them.

## 4. Keep the house style

After every choice the user makes between options (a look, a voice, music, a cover, a
reference), add one dated line to the house-style file: what they chose or turned down
and why, in their words. When a preference comes back across projects, move it to
Standing preferences. Read the file at every brief; it is how taste carries from one
video to the next.
