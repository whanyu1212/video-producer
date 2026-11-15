import takeWords from '../public/assets/narration/narration_v1.words.json';
import {wordStart, type Word} from './lib/words';

export const NARRATION_SRC = 'assets/narration/narration_v1.mp3';

/**
 * The take plays as slices with a pause inserted at each paragraph break, so the
 * picture can breathe. Every cut sits in measured silence on the take.
 */
export type NarrationClip = {from: number; to: number; at: number};

const LEAD_IN = 0.5;
const TAKE_END = 21.43;
/** Cut points in the take and the pause inserted at each. */
const PAUSES: readonly {at: number; pause: number}[] = [
	{at: 9.13, pause: 0.4}, // after "sync."
	{at: 16.32, pause: 0.4}, // after "sooner or later."
];

const buildClips = (): NarrationClip[] => {
	const clips: NarrationClip[] = [];
	let from = 0;
	let at = LEAD_IN;
	for (const {at: cut, pause} of [...PAUSES, {at: TAKE_END, pause: 0}]) {
		clips.push({from, to: cut, at});
		at += cut - from + pause;
		from = cut;
	}
	return clips;
};
export const NARRATION_CLIPS: readonly NarrationClip[] = buildClips();

const onTimeline = (takeSecond: number) => {
	const clip = NARRATION_CLIPS.find((c) => takeSecond >= c.from && takeSecond < c.to) ?? NARRATION_CLIPS[NARRATION_CLIPS.length - 1];
	return takeSecond - clip.from + clip.at;
};

/** Every spoken word, timed on the video timeline (seconds). */
export const words: readonly Word[] = takeWords.map((word) => {
	const clip = NARRATION_CLIPS.find((c) => word.start >= c.from && word.start < c.to);
	if (!clip) {
		throw new Error(`Word "${word.text}" at ${word.start}s falls outside every narration clip`);
	}
	const shift = clip.at - clip.from;
	return {text: word.text, start: word.start + shift, end: word.end + shift};
});

/** Timeline second when a word is spoken; `nth` picks a later occurrence. */
export const cue = (text: string, nth = 0) => wordStart(words, text, nth);

/** End of the speech in "Take one free minute." (measured on the take: 20.83 s). */
export const SPEECH_END = onTimeline(20.83);
export const DURATION_SECONDS = 24;

/** Beat starts, each a little before the word that opens it. */
export const SECTIONS = [
	{id: 'hook', start: 0},
	{id: 'title', start: cue('When', 1) - 0.15}, // "When it happens on most laptops"
	{id: 'risk', start: cue('more') - 0.3},
	{id: 'good', start: cue('good') - 0.3},
	{id: 'action', start: cue('Take') - 0.3},
] as const;

/** The row of laptops in the risk beat lights up on "on most laptops, sooner or later." */
export const LAPTOPS_LIGHT = cue('most');

export const MUSIC = {
	src: 'assets/music/music_bed_v1.mp3',
	baseDb: -9,
	duckDb: 9,
	fadeIn: 0.5,
	fadeOut: 2,
};

/** Effects: a soft whoosh under every beat change, a chime on "fixed." */
export const SFX: readonly {src: string; at: number; volume: number}[] = [
	...SECTIONS.slice(1).map((section) => ({src: 'assets/sfx/whoosh_v1.mp3', at: section.start - 0.4, volume: 0.09})),
	{src: 'assets/sfx/chime_v1.mp3', at: cue('fixed.') - 0.05, volume: 0.9},
];
