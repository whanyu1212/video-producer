/** One spoken word, timed in seconds from the start of its audio file (narrate.py / transcribe.py output). */
export type Word = {text: string; start: number; end: number};

export type Span = {start: number; end: number};

const normalize = (text: string): string => text.toLowerCase().replace(/[^\p{L}\p{N}']+/gu, '');

/**
 * Start time of a spoken word, so animation lands on the voice instead of a guess.
 * `nth` picks a later occurrence of the same word (0 = first).
 */
export const wordStart = (words: readonly Word[], text: string, nth = 0): number => {
	const target = normalize(text);
	const match = words.filter((word) => normalize(word.text) === target)[nth];
	if (!match) {
		throw new Error(`Word "${text}" (occurrence ${nth}) is not in the narration`);
	}
	return match.start;
};

/** Stretches of continuous speech on the video timeline; gaps shorter than `maxGap` are bridged. */
export const speechSpans = (words: readonly Word[], offset: number, maxGap = 0.4): Span[] => {
	const spans: Span[] = [];
	for (const word of words) {
		const start = word.start + offset;
		const end = word.end + offset;
		const last = spans[spans.length - 1];
		if (last && start - last.end <= maxGap) {
			last.end = end;
		} else {
			spans.push({start, end});
		}
	}
	return spans;
};
