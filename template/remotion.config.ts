import {Config} from '@remotion/cli/config';

// PNG frames keep dark gradients clean; JPEG capture bands them.
Config.setVideoImageFormat('png');
Config.setPixelFormat('yuv420p');
Config.setCodec('h264');
Config.setCrf(16);
