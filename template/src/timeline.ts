import {narrationClips, timelineWords, type Pause} from './lib/narration';
import {wordStart, type Word} from './lib/words';

export type Effect = {
	/** Relative to public/. */
	src: string;
	/** Where it plays on the video timeline, in seconds. */
	at: number;
	/** Linear gain. */
	volume: number;
};

export type Soundtrack = {
	/**
	 * `src` is relative to public/; `at` is where the take starts on the timeline, in seconds;
	 * `pauses` insert silence at measured cut points of the take (silence_cuts.py).
	 */
	narration?: {src: string; at: number; words: readonly Word[]; pauses?: readonly Pause[]};
	/**
	 * `fadeIn` / `fadeOut` are seconds at the start and end of the video. The music stays
	 * ducked through gaps between words of up to `duckThrough` seconds (default 0.4). A gap
	 * on the timeline is the take's own silence plus any inserted pause: set it above the
	 * longest gap the music should stay down through, or it swells in each one.
	 */
	music?: {src: string; baseDb: number; duckDb: number; fadeIn?: number; fadeOut?: number; duckThrough?: number};
	/** Every sound effect, one entry per action, each with a comment naming the action it marks. */
	effects?: readonly Effect[];
};

/** Set from the measured narration length plus room for the ending, never a guess. */
export const DURATION_SECONDS = 10;

export const soundtrack: Soundtrack = {};

const {narration} = soundtrack;

/** The take's slices on the video timeline (one slice when there are no pauses). */
export const clips = narration ? narrationClips(narration.at, narration.pauses) : [];

/** Every spoken word, timed on the video timeline (lead-in and pauses applied). */
export const words: readonly Word[] = narration ? timelineWords(narration.words, clips) : [];

/** Video time a word is spoken; `nth` picks a later occurrence (0 = first). */
export const cue = (text: string, nth = 0): number => wordStart(words, text, nth);
