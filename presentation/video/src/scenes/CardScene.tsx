import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig, Easing} from 'remotion';
import {theme} from '../theme';
import {Tile} from '../script';
import {Caption} from './Caption';

const ease = (frame: number, from: number, to: number) =>
  interpolate(frame, [from, to], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });

const accentOf = (t: Tile, i: number) =>
  t.color === 'blue' ? theme.blue : t.color === 'orange' ? theme.orange : t.color === 'ink' ? theme.ink : i === 0 ? theme.blue : theme.orange;

// A statement card: a heading, one or two large tiles that appear in turn, and a small note.
export const CardScene: React.FC<{heading?: string; tiles: Tile[]; note?: string; caption: string}> = ({heading, tiles, note, caption}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const head = ease(frame, 0, fps * 0.6);
  const wide = tiles.length === 1;
  return (
    <AbsoluteFill>
      <div style={{position: 'absolute', left: 0, right: 0, top: 0, bottom: 120, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '0 120px'}}>
        {heading ? (
          <div style={{fontSize: 46, color: theme.muted, marginBottom: 54, opacity: head, transform: `translateY(${(1 - head) * 16}px)`}}>{heading}</div>
        ) : null}
        <div style={{display: 'flex', gap: 40, justifyContent: 'center', width: '100%'}}>
          {tiles.map((t, i) => {
            const o = ease(frame, fps * (0.5 + i * 0.9), fps * (1.1 + i * 0.9));
            return (
              <div
                key={i}
                style={{
                  width: wide ? 1100 : 760,
                  background: '#ffffff',
                  border: '2px solid #e6e5e1',
                  borderTop: `12px solid ${accentOf(t, i)}`,
                  borderRadius: 22,
                  padding: '44px 48px 46px',
                  boxShadow: '0 12px 36px rgba(0,0,0,0.07)',
                  opacity: o,
                  transform: `translateY(${(1 - o) * 30}px)`,
                  textAlign: 'center',
                }}
              >
                <div style={{fontSize: wide ? 96 : 110, fontWeight: 800, letterSpacing: -3, lineHeight: 1.05, color: accentOf(t, i)}}>{t.value}</div>
                <div style={{fontSize: 34, lineHeight: 1.3, color: theme.ink, marginTop: 22}}>{t.label}</div>
              </div>
            );
          })}
        </div>
        {note ? (
          <div style={{marginTop: 40, fontSize: 28, color: theme.faint, opacity: ease(frame, fps * 1.6, fps * 2.2)}}>{note}</div>
        ) : null}
      </div>
      <Caption text={caption} />
    </AbsoluteFill>
  );
};
