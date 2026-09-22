import React from 'react';
import {AbsoluteFill, Audio, Sequence, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {ResolvedScene} from './script';
import {theme} from './theme';
import {TitleCard} from './scenes/TitleCard';
import {CloseCard} from './scenes/CloseCard';
import {ImageScene} from './scenes/ImageScene';
import {FrameScene} from './scenes/FrameScene';
import {TerminalScene} from './scenes/TerminalScene';
import {CardScene} from './scenes/CardScene';
import {TimelapseScene} from './scenes/TimelapseScene';

import {FADE_FRAMES} from './theme';

const SceneBody: React.FC<{scene: ResolvedScene}> = ({scene}) => {
  const v = scene.visual;
  switch (v.kind) {
    case 'title':
      return <TitleCard headline={v.headline} tiles={v.tiles ?? []} footnote={v.footnote} />;
    case 'card':
      return <CardScene heading={v.heading} tiles={v.tiles} note={v.note} caption={scene.caption} />;
    case 'timelapse':
      return (
        <TimelapseScene
          dir={v.dir}
          from={v.from}
          to={v.to}
          pad={v.pad}
          ext={v.ext}
          width={v.width}
          height={v.height}
          layout={v.layout}
          questions={v.questions}
          caption={scene.caption}
        />
      );
    case 'close':
      return <CloseCard caption={scene.caption} lines={v.lines} />;
    case 'image':
      return <ImageScene src={v.src} caption={scene.caption} highlights={v.highlights} />;
    case 'frame':
      return <FrameScene src={v.src} width={v.width} height={v.height} zoom={v.zoom} labels={v.labels} caption={scene.caption} />;
    case 'terminal':
      return (
        <TerminalScene title={v.title} status={v.status} blocks={v.blocks} hold={v.hold} keyCitations={v.keyCitations} caption={scene.caption} />
      );
    default:
      return null;
  }
};

// One scene: its voice-over, its visual, and a gentle fade in and out over the light ground.
const SceneShell: React.FC<{scene: ResolvedScene}> = ({scene}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const opacity = interpolate(
    frame,
    [0, FADE_FRAMES, durationInFrames - FADE_FRAMES, durationInFrames - 1],
    [0, 1, 1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );
  return (
    <AbsoluteFill style={{backgroundColor: theme.bg}}>
      <Audio src={scene.voiceSrc} />
      <AbsoluteFill style={{opacity}}>
        <SceneBody scene={scene} />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

export const ScryVideo: React.FC<{scenes: ResolvedScene[]}> = ({scenes}) => {
  return (
    <AbsoluteFill style={{backgroundColor: theme.bg, fontFamily: theme.sans, color: theme.ink}}>
      {scenes.map((sc) => (
        <Sequence key={sc.id} name={sc.id} from={sc.from} durationInFrames={sc.durationInFrames}>
          <SceneShell scene={sc} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
