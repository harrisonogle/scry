import raw from '../script.json';

export type Block =
  | {kind: 'cmd'; text: string}
  | {kind: 'note'; text: string}
  | {kind: 'call'; name: string; args: string; results: string[]}
  | {kind: 'answer'; lines: string[]};

export type FrameLabel = {x: number; y: number; color: 'blue' | 'orange'; text: string};

export type Visual =
  | {kind: 'title'}
  | {kind: 'close'; lines: string[]}
  | {kind: 'terminal'; title: string; status: string; source?: string; blocks: Block[]}
  | {kind: 'frame'; src: string; zoom: {cx: number; cy: number; scale: number}; labels: FrameLabel[]}
  | {
      kind: 'image';
      src: string;
      // Optional soft outlines drawn over the image, in fractions of its width and height,
      // shown between two fractions of the scene's duration.
      highlights?: {rect: [number, number, number, number]; from: number; until: number; color: 'blue' | 'orange'}[];
    };

export type Scene = {
  id: string;
  visual: Visual;
  caption: string;
  voice: string;
  optional?: boolean;
};

export type Script = {
  fps: number;
  width: number;
  height: number;
  padSeconds: number;
  scenes: Scene[];
};

// A scene after calculateMetadata has measured its voice file.
export type ResolvedScene = Scene & {
  voiceSrc: string;
  voiceSeconds: number;
  from: number;
  durationInFrames: number;
};

export const script = raw as Script;
