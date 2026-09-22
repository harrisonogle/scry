import raw from '../script.json';

export type Block =
  | {kind: 'cmd'; text: string}
  | {kind: 'note'; text: string}
  | {kind: 'call'; name: string; args: string; results: string[]}
  | {kind: 'answer'; lines: string[]}
  | {kind: 'meta'; text: string};

export type FrameLabel = {x: number; y: number; color: 'blue' | 'orange'; text: string};

export type Visual =
  | {kind: 'title'}
  | {kind: 'close'; lines: string[]}
  | {
      kind: 'terminal';
      title: string;
      status: string;
      source?: string;
      // Share of the scene that keeps the finished transcript on screen (default 0.18).
      hold?: number;
      // Citation ids drawn orange; every other id is blue.
      keyCitations?: string[];
      blocks: Block[];
    }
  | {
      kind: 'frame';
      src: string;
      // Pixel size of the image (default 1920 x 1080); zoom and labels are in image pixels.
      width?: number;
      height?: number;
      zoom: {cx: number; cy: number; scale: number};
      labels: FrameLabel[];
    }
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
  // Numbers or wording not yet frozen by the coordinator.
  draft?: boolean;
};

export type Script = {
  version?: number;
  fps: number;
  width: number;
  height: number;
  padSeconds: number;
  // The platform's ceiling for the rendered video, pads included; the build refuses to exceed it.
  maxSeconds?: number;
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
