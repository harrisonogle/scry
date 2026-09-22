import React from 'react';
import {AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig, Easing} from 'remotion';
import {theme} from '../theme';
import {Caption} from './Caption';

type Highlight = {rect: [number, number, number, number]; from: number; until: number; color: 'blue' | 'orange'};

// A chart (3840 x 2160 PNG) shown at 1707 x 960 above the caption band, with a barely visible drift.
export const ImageScene: React.FC<{src: string; caption: string; highlights?: Highlight[]}> = ({
  src,
  caption,
  highlights,
}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const p = frame / Math.max(1, durationInFrames - 1);
  const scale = interpolate(p, [0, 1], [1, 1.02]);
  const W = 1707;
  const H = 960;
  return (
    <AbsoluteFill>
      <div
        style={{
          position: 'absolute',
          left: (1920 - W) / 2,
          top: 18,
          width: W,
          height: H,
          transform: `scale(${scale})`,
          transformOrigin: '50% 40%',
        }}
      >
        <Img src={staticFile(`img/${src}`)} style={{width: W, height: H, display: 'block'}} />
        {(highlights ?? []).map((h, i) => {
          // Fade over 6 % of the scene at each end, or less when the window is short (the range must stay increasing).
          const fade = Math.min(0.06, (h.until - h.from) * 0.4);
          const o = interpolate(p, [h.from, h.from + fade, h.until - fade, h.until], [0, 1, 1, 0], {
            extrapolateLeft: 'clamp',
            extrapolateRight: 'clamp',
            easing: Easing.inOut(Easing.quad),
          });
          const [x, y, w, hh] = h.rect;
          return (
            <div
              key={i}
              style={{
                position: 'absolute',
                left: x * W - 8,
                top: y * H - 8,
                width: w * W + 16,
                height: hh * H + 16,
                border: `6px solid ${h.color === 'blue' ? theme.blue : theme.orange}`,
                borderRadius: 22,
                opacity: o * 0.9,
                boxShadow: `0 0 0 6px ${h.color === 'blue' ? theme.blueSoft : theme.orangeSoft}`,
              }}
            />
          );
        })}
      </div>
      <Caption text={caption} />
    </AbsoluteFill>
  );
};
