import React from 'react';
import {AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig, Easing} from 'remotion';
import {theme} from '../theme';
import {Caption} from './Caption';
import {FrameLabel} from '../script';

// The cited frame (boxes already drawn on it) with a slow zoom towards `zoom` (a point in image pixels and the
// final scale). The image is fitted to the canvas first; the zoom moves the point towards the centre but never
// lets the image's edge into view. Labels are pinned to image pixels and drawn in screen space, so they keep
// their size while the image grows under them.
type Props = {
  src: string;
  width?: number;
  height?: number;
  caption: string;
  zoom: {cx: number; cy: number; scale: number};
  labels: FrameLabel[];
};

const colourOf = (c: FrameLabel['color']) => (c === 'orange' ? theme.orange : c === 'aqua' ? theme.aqua : theme.blue);

export const FrameScene: React.FC<Props> = ({src, width, height, caption, zoom, labels}) => {
  const frame = useCurrentFrame();
  const {durationInFrames, fps} = useVideoConfig();
  const p = interpolate(frame, [fps * 0.6, durationInFrames - fps * 0.8], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.inOut(Easing.cubic),
  });
  const W = width ?? 1920;
  const H = height ?? 1080;
  const k = Math.min(1920 / W, 1080 / H);
  const s = k * (1 + p * (zoom.scale - 1));
  const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));
  // Where the zoom point wants to be (the centre), limited so the image always covers the canvas where it can.
  const fitX = (1920 - W * s) / 2;
  const fitY = (1080 - H * s) / 2;
  const tx = W * s <= 1920 ? fitX : clamp(960 - zoom.cx * s, 1920 - W * s, 0);
  const ty = H * s <= 1080 ? fitY : clamp(540 - zoom.cy * s, 1080 - H * s, 0);
  const labelOpacity = interpolate(p, [0.05, 0.25], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return (
    <AbsoluteFill style={{overflow: 'hidden', background: '#e9e9e6'}}>
      <div
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          width: W,
          height: H,
          transform: `translate(${tx}px, ${ty}px) scale(${s})`,
          transformOrigin: '0 0',
        }}
      >
        <Img src={staticFile(`img/${src}`)} style={{width: W, height: H, display: 'block'}} />
      </div>
      {labels.map((l, i) => (
        <div
          key={i}
          style={{
            position: 'absolute',
            left: tx + l.x * s,
            top: ty + l.y * s,
            fontFamily: theme.mono,
            fontSize: 22,
            lineHeight: 1,
            padding: '8px 12px',
            borderRadius: 6,
            background: colourOf(l.color),
            color: '#fff',
            opacity: labelOpacity,
            whiteSpace: 'nowrap',
            boxShadow: '0 4px 14px rgba(0,0,0,0.25)',
          }}
        >
          {l.text}
        </div>
      ))}
      <Caption text={caption} pill position="top" />
    </AbsoluteFill>
  );
};
