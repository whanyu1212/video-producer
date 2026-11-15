import {AbsoluteFill} from 'remotion';
import {theme} from '../theme';

type ThumbnailProps = {headline: string};

/** A still: 1-5 words that stay legible when shrunk to ~170 px wide in a feed. */
export const Thumbnail = ({headline}: ThumbnailProps) => (
	<AbsoluteFill style={{backgroundColor: theme.background, justifyContent: 'center', padding: '0 80px', fontFamily: theme.font}}>
		<div style={{color: theme.text, fontSize: 150, fontWeight: 800, lineHeight: 1}}>{headline}</div>
		<div style={{height: 16, width: 220, backgroundColor: theme.accent, marginTop: 40}} />
	</AbsoluteFill>
);
