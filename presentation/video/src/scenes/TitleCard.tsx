import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig, Easing} from 'remotion';
import {theme} from '../theme';

const ease = (frame: number, from: number, to: number) =>
  interpolate(frame, [from, to], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });

export const TitleCard: React.FC<{caption: string}> = ({caption}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const word = ease(frame, 0, fps * 0.8);
  const bars = ease(frame, fps * 0.5, fps * 1.4);
  const sub = ease(frame, fps * 0.9, fps * 1.7);
  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center'}}>
      <div style={{width: 1400, display: 'flex', flexDirection: 'column', alignItems: 'flex-start'}}>
        <div
          style={{
            fontSize: 250,
            fontWeight: 800,
            letterSpacing: -8,
            lineHeight: 1,
            color: theme.ink,
            opacity: word,
            transform: `translateY(${(1 - word) * 30}px)`,
          }}
        >
          scry
        </div>
        <div style={{display: 'flex', gap: 14, marginTop: 34, height: 16}}>
          <div style={{width: 420 * bars, height: 16, borderRadius: 8, background: theme.blue}} />
          <div style={{width: 180 * bars, height: 16, borderRadius: 8, background: theme.orange}} />
        </div>
        <div
          style={{
            marginTop: 44,
            fontSize: 46,
            lineHeight: 1.3,
            color: theme.muted,
            maxWidth: 1300,
            opacity: sub,
            transform: `translateY(${(1 - sub) * 24}px)`,
          }}
        >
          {caption}
        </div>
      </div>
    </AbsoluteFill>
  );
};
