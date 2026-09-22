import type { TrackKind } from '../lib/types';

export type LampColour = 'amber' | 'red' | 'white' | 'magenta' | 'cyan' | 'green';

/** Content kind → lamp colour. CSS colour comes from [data-kind] in tokens.css; this is for lamps. */
export const KIND_LAMP: Record<TrackKind, LampColour> = {
  music: 'amber',
  break: 'magenta',
  bumper: 'cyan',
  unknown: 'amber',
};

export const KIND_LABEL: Record<TrackKind, string> = {
  music: 'Music',
  break: 'News bulletin',
  bumper: 'Station ID',
  unknown: 'On air',
};
