import React from 'react';
import {AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig, Easing} from 'remotion';
import {theme} from '../theme';
import {Caption} from './Caption';
import {FADE_FRAMES} from '../theme';

type Props = {
  dir: string;
  from: number;
  to: number;
  pad?: number;
  ext?: string;
  width?: number;
  height?: number;
  layout?: 'full' | 'side';
  questions?: string[];
  caption: string;
};

// A sequence of stills played once across the scene (its rate follows the voice-over's length), letterboxed
// in a framed box; layout 'side' lists the questions beside it, appearing one by one.
export const TimelapseScene: React.FC<Props> = ({dir, from, to, pad, ext, width, height, layout, questions, caption}) => {
  const frame = useCurrentFrame();
  const {durationInFrames, fps} = useVideoConfig();
  const q = interpolate(frame, [FADE_FRAMES, durationInFrames - FADE_FRAMES], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const count = to - from + 1;
  const idx = from + Math.min(count - 1, Math.floor(q * count));
  const name = String(idx).padStart(pad ?? 2, '0');
  const aspect = (width ?? 2048) / (height ?? 1080);
  const side = layout === 'side';
  const boxW = side ? 1180 : 1707;
  const boxH = Math.round(boxW / aspect);
  const boxLeft = side ? 80 : (1920 - boxW) / 2;
  const boxTop = side ? Math.round((960 - boxH) / 2) : Math.max(18, Math.round((984 - boxH) / 2));
  const qs = questions ?? [];
  return (
    <AbsoluteFill>
      <div
        style={{
          position: 'absolute',
          left: boxLeft,
          top: boxTop,
          width: boxW,
          height: boxH,
          borderRadius: 14,
          overflow: 'hidden',
          background: '#1b1d22',
          boxShadow: '0 16px 48px rgba(0,0,0,0.22)',
        }}
      >
        <Img src={staticFile(`img/${dir}/${name}.${ext ?? 'png'}`)} style={{width: boxW, height: boxH, display: 'block', objectFit: 'contain'}} />
        <div
          style={{
            position: 'absolute',
            left: 0,
            bottom: 0,
            height: 6,
            width: `${(q * 100).toFixed(2)}%`,
            background: theme.orange,
          }}
        />
      </div>
      {side ? (
        <div style={{position: 'absolute', left: 1320, top: boxTop, width: 520, display: 'flex', flexDirection: 'column', gap: 22}}>
          {qs.map((text, i) => {
            const at = 0.1 + (i * 0.75) / Math.max(1, qs.length);
            const o = interpolate(q, [at, at + 0.06], [0, 1], {
              extrapolateLeft: 'clamp',
              extrapolateRight: 'clamp',
              easing: Easing.out(Easing.cubic),
            });
            return (
              <div
                key={i}
                style={{
                  display: 'flex',
                  gap: 16,
                  alignItems: 'flex-start',
                  opacity: o,
                  transform: `translateX(${(1 - o) * 24}px)`,
                  fontSize: 34,
                  lineHeight: 1.25,
                  color: theme.ink,
                }}
              >
                <div style={{flex: '0 0 auto', width: 14, height: 14, borderRadius: 7, marginTop: 14, background: i % 2 ? theme.orange : theme.blue}} />
                <div>{text}</div>
              </div>
            );
          })}
        </div>
      ) : null}
      <Caption text={caption} />
    </AbsoluteFill>
  );
};
