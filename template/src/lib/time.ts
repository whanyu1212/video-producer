export const FPS = 30;

/** Seconds to whole frames at the project frame rate. */
export const sec = (seconds: number): number => Math.round(seconds * FPS);
