import {Composition, Still} from 'remotion';
import {FPS, sec} from './lib/time';
import {Thumbnail} from './scenes/Thumbnail';
import {DURATION_SECONDS} from './timeline';
import {Video} from './Video';

export const Root = () => (
	<>
		<Composition id="Main" component={Video} durationInFrames={sec(DURATION_SECONDS)} fps={FPS} width={1920} height={1080} />
		<Composition id="Vertical" component={Video} durationInFrames={sec(DURATION_SECONDS)} fps={FPS} width={1080} height={1920} />
		<Still id="Thumbnail" component={Thumbnail} defaultProps={{headline: 'Say it short'}} width={1280} height={720} />
	</>
);
