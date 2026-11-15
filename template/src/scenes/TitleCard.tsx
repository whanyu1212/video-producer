import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {theme} from '../theme';

type TitleCardProps = {kicker: string; headline: string};

/** A starting point, not a finished look: restyle it to the project's art direction. */
export const TitleCard = ({kicker, headline}: TitleCardProps) => {
	const frame = useCurrentFrame();
	const {fps, width, height} = useVideoConfig();
	const unit = Math.min(width, height) / 100;
	const seconds = frame / fps;

	const kickerIn = interpolate(seconds, [0, 0.4], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
	const headlineIn = spring({frame: frame - Math.round(0.15 * fps), fps, config: {damping: 200}});
	const barWidth = interpolate(seconds, [0.3, 0.9], [0, 18 * unit], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
	// A slow drift keeps held cards alive so they never read as a frozen frame.
	const drift = 1 + seconds * 0.006;

	return (
		<AbsoluteFill style={{justifyContent: 'center', padding: `0 ${10 * unit}px`, fontFamily: theme.font, transform: `scale(${drift})`}}>
			<div style={{color: theme.accent, fontSize: 3.2 * unit, fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase', opacity: kickerIn, transform: `translateY(${(1 - kickerIn) * 2 * unit}px)`}}>
				{kicker}
			</div>
			<div style={{color: theme.text, fontSize: 9 * unit, fontWeight: 800, lineHeight: 1.05, marginTop: 2 * unit, opacity: headlineIn, transform: `translateY(${(1 - headlineIn) * 4 * unit}px)`}}>
				{headline}
			</div>
			<div style={{height: 0.6 * unit, width: barWidth, backgroundColor: theme.accent, marginTop: 4 * unit}} />
		</AbsoluteFill>
	);
};
