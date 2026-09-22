import React from 'react';
import {AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig, Easing} from 'remotion';
import {theme} from '../theme';
import {Caption} from './Caption';

import {FrameLabel} from '../script';

// The cited frame (1920 x 1080, boxes already drawn on it) with a slow zoom towards `zoom` (a point in frame
// pixels and the final scale) and small labels placed in frame pixels, all from script.json.
type Props = {src: string; caption: string; zoom: {cx: number; cy: number; scale: number}; labels: FrameLabel[]};

export const FrameScene: React.FC<Props> = ({src, caption, zoom, labels}) => {
  const frame = useCurrentFrame();
  const {durationInFrames, fps} = useVideoConfig();
  const p = interpolate(frame, [fps * 0.6, durationInFrames - fps * 0.8], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.inOut(Easing.cubic),
  });
  const s = 1 + p * (zoom.scale - 1);
  const tx = p * (960 - zoom.cx * zoom.scale);
  const ty = p * (540 - zoom.cy * zoom.scale);
  const label = interpolate(p, [0.75, 1], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return (
    <AbsoluteFill style={{overflow: 'hidden'}}>
      <div
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          width: 1920,
          height: 1080,
          transform: `translate(${tx}px, ${ty}px) scale(${s})`,
          transformOrigin: '0 0',
        }}
      >
        <Img src={staticFile(`img/${src}`)} style={{width: 1920, height: 1080, display: 'block'}} />
        {labels.map((l, i) => (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: l.x,
              top: l.y,
              fontFamily: theme.mono,
              fontSize: 11,
              lineHeight: 1,
              padding: '5px 7px',
              borderRadius: 4,
              background: l.color === 'orange' ? theme.orange : theme.blue,
              color: '#fff',
              opacity: label,
              whiteSpace: 'nowrap',
            }}
          >
            {l.text}
          </div>
        ))}
      </div>
      <Caption text={caption} pill />
    </AbsoluteFill>
  );
};
