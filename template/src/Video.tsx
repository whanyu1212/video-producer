import {AbsoluteFill, Audio, interpolate, Sequence, staticFile, useVideoConfig} from 'remotion';
import {duckedVolume} from './lib/duck';
import {sec} from './lib/time';
import {speechSpans} from './lib/words';
import {TitleCard} from './scenes/TitleCard';
import {clips, DURATION_SECONDS, soundtrack, words} from './timeline';
import {theme} from './theme';

const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

const Soundtrack = () => {
	const {fps} = useVideoConfig();
	const {narration, music, effects = []} = soundtrack;
	const spans = speechSpans(words, 0, music?.duckThrough);
	return (
		<>
			{narration &&
				clips.map((clip) => (
					<Sequence
						key={clip.from}
						from={sec(clip.at)}
						durationInFrames={Number.isFinite(clip.to) ? sec(clip.to - clip.from) : undefined}
						layout="none"
					>
						<Audio src={staticFile(narration.src)} trimBefore={sec(clip.from)} />
					</Sequence>
				))}
			{music && (
				<Audio
					src={staticFile(music.src)}
					volume={(frame) => {
						const t = frame / fps;
						const fadeIn = music.fadeIn ? interpolate(t, [0, music.fadeIn], [0, 1], clamp) : 1;
						const fadeOut = music.fadeOut ? interpolate(t, [DURATION_SECONDS - music.fadeOut, DURATION_SECONDS], [1, 0], clamp) : 1;
						return Math.min(fadeIn, fadeOut) * duckedVolume(t, spans, {baseDb: music.baseDb, duckDb: music.duckDb, rampSeconds: 0.25});
					}}
				/>
			)}
			{effects.map((effect, index) => (
				<Sequence key={`${effect.src}-${index}`} from={Math.max(0, sec(effect.at))} layout="none">
					<Audio src={staticFile(effect.src)} volume={effect.volume} />
				</Sequence>
			))}
		</>
	);
};

/** The timeline: one <Sequence> per beat, timed with sec() and cue() from the plan in project.md. */
export const Video = () => (
	<AbsoluteFill style={{backgroundColor: theme.background}}>
		<Sequence from={0} durationInFrames={sec(4)}>
			<TitleCard kicker="Your product" headline="Say one thing well" />
		</Sequence>
		<Sequence from={sec(4)} durationInFrames={sec(6)}>
			<TitleCard kicker="Then" headline="Show it working" />
		</Sequence>
		<Soundtrack />
	</AbsoluteFill>
);
