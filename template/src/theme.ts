import {loadFont} from '@remotion/google-fonts/Inter';

const {fontFamily} = loadFont('normal', {weights: ['400', '600', '800'], subsets: ['latin']});

/** Replace with the project's own look (see the Look section of project.md). */
export const theme = {
	background: '#0f1115',
	surface: '#1a1d24',
	text: '#f4f1ea',
	muted: '#9aa0aa',
	accent: '#ff7a45',
	font: fontFamily,
};
