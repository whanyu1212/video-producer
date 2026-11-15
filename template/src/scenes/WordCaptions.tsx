import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import type {Word} from '../lib/words';
import {theme} from '../theme';

type WordCaptionsProps = {
	words: readonly Word[];
	/** Seconds added to every word; 0 for `words` from timeline.ts, which are already on the video timeline. */
	offset?: number;
	maxWordsPerLine?: number;
};

const groupLines = (words: readonly Word[], maxWords: number, maxGap: number): Word[][] => {
	const lines: Word[][] = [];
	for (const word of words) {
		const line = lines[lines.length - 1];
		const previous = line?.[line.length - 1];
		if (line && previous && line.length < maxWords && word.start - previous.end <= maxGap) {
			line.push(word);
		} else {
			lines.push([word]);
		}
	}
	return lines;
};

/** Burned-in captions: the current line, with the spoken word highlighted. */
export const WordCaptions = ({words, offset = 0, maxWordsPerLine = 6}: WordCaptionsProps) => {
	const frame = useCurrentFrame();
	const {fps, width, height} = useVideoConfig();
	const unit = Math.min(width, height) / 100;
	const t = frame / fps - offset;
	const line = groupLines(words, maxWordsPerLine, 0.5).find((candidate) => t >= candidate[0].start - 0.1 && t <= candidate[candidate.length - 1].end + 0.3);
	if (!line) {
		return null;
	}
	const spokenIndex = line.reduce((latest, word, index) => (t >= word.start ? index : latest), -1);
	// On a vertical frame the bottom 15% sits under TikTok's and Reels' own buttons and text.
	const bottom = height > width ? height * 0.15 : 8 * unit;
	return (
		<AbsoluteFill style={{justifyContent: 'flex-end', alignItems: 'center', paddingBottom: bottom}}>
			<div style={{fontFamily: theme.font, fontWeight: 800, fontSize: 5 * unit, color: theme.text, backgroundColor: 'rgba(0,0,0,0.55)', padding: `${unit}px ${2.5 * unit}px`, borderRadius: 1.5 * unit, textAlign: 'center', maxWidth: '86%'}}>
				{line.map((word, index) => (
					<span key={`${word.start}-${index}`} style={{color: index === spokenIndex ? theme.accent : theme.text}}>
						{index > 0 ? ' ' : ''}
						{word.text}
					</span>
				))}
			</div>
		</AbsoluteFill>
	);
};
