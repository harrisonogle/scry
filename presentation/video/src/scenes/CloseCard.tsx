import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig, Easing} from 'remotion';
import {theme} from '../theme';

const ease = (frame: number, from: number, to: number) =>
  interpolate(frame, [from, to], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });

// The closing card: the repo name and what the numbers rest on.
export const CloseCard: React.FC<{caption: string; lines: string[]}> = ({caption, lines}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const word = ease(frame, 0, fps * 0.7);
  const repo = ease(frame, fps * 0.4, fps * 1.1);
  const line1 = ease(frame, fps * 1.0, fps * 1.7);
  const line2 = ease(frame, fps * 1.6, fps * 2.3);
  const row = (t: number, node: React.ReactNode, style: React.CSSProperties = {}) => (
    <div style={{opacity: t, transform: `translateY(${(1 - t) * 20}px)`, ...style}}>{node}</div>
  );
  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center'}}>
      <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 30}}>
        {row(word, 'scry', {fontSize: 170, fontWeight: 800, letterSpacing: -6, lineHeight: 1, color: theme.ink})}
        {row(repo, caption, {fontSize: 54, color: theme.blue, fontFamily: theme.mono, marginTop: 10})}
        <div style={{display: 'flex', gap: 14, marginTop: 10}}>
          <div style={{width: 300 * repo, height: 12, borderRadius: 6, background: theme.blue}} />
          <div style={{width: 130 * repo, height: 12, borderRadius: 6, background: theme.orange}} />
        </div>
        {lines[0] ? row(line1, lines[0], {fontSize: 50, color: theme.ink, marginTop: 20}) : null}
        {lines[1] ? row(line2, lines[1], {fontSize: 42, color: theme.muted}) : null}
      </div>
    </AbsoluteFill>
  );
};
