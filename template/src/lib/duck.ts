import type {Span} from './words';

export type DuckOptions = {
	/** Music level with no speech, in dB (0 = as composed). */
	baseDb: number;
	/** How far the music drops under speech, in dB. */
	duckDb: number;
	/** Fade time into and out of each dip, in seconds. */
	rampSeconds: number;
};

const dbToGain = (db: number): number => 10 ** (db / 20);

/** Music gain at `seconds`, dipping under speech so narration stays clear. */
export const duckedVolume = (seconds: number, spans: readonly Span[], {baseDb, duckDb, rampSeconds}: DuckOptions): number => {
	let depth = 0;
	for (const span of spans) {
		const intoSpan = (seconds - (span.start - rampSeconds)) / rampSeconds;
		const beforeEnd = (span.end + rampSeconds - seconds) / rampSeconds;
		depth = Math.max(depth, Math.min(1, intoSpan, beforeEnd));
	}
	return dbToGain(baseDb - depth * duckDb);
};
