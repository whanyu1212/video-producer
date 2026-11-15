import type {Word} from './words';

/** Silence inserted into the narration at a cut point of the take. */
export type Pause = {
	/** Cut point in the take, in seconds of the file: a silence measured with silence_cuts.py. */
	after: number;
	/** Seconds of silence inserted there. */
	seconds: number;
};

/** A slice of the take and where it plays on the video timeline. `to` is Infinity for the last slice. */
export type NarrationClip = {from: number; to: number; at: number};

/** The take as slices separated by the pauses, the first starting at `at` on the timeline. */
export const narrationClips = (at: number, pauses: readonly Pause[] = []): NarrationClip[] => {
	const clips: NarrationClip[] = [];
	let from = 0;
	let start = at;
	for (const pause of [...pauses].sort((a, b) => a.after - b.after)) {
		clips.push({from, to: pause.after, at: start});
		start += pause.after - from + pause.seconds;
		from = pause.after;
	}
	clips.push({from, to: Infinity, at: start});
	return clips;
};

/** A second of the take, moved onto the video timeline. */
export const onTimeline = (clips: readonly NarrationClip[], takeSecond: number): number => {
	const clip = clips.find((candidate) => takeSecond < candidate.to) ?? clips[clips.length - 1];
	return takeSecond - clip.from + clip.at;
};

/** Every word of the take, timed on the video timeline; a word moves with the slice it starts in. */
export const timelineWords = (words: readonly Word[], clips: readonly NarrationClip[]): Word[] =>
	words.map((word) => {
		const shift = onTimeline(clips, word.start) - word.start;
		return {text: word.text, start: word.start + shift, end: word.end + shift};
	});
