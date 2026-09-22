import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig, Easing} from 'remotion';
import {theme} from '../theme';
import {Tile} from '../script';

const ease = (frame: number, from: number, to: number) =>
  interpolate(frame, [from, to], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });

// The headline card: the wordmark, one line, and three stat tiles from script.json that appear in turn
// as the voice-over reaches them. A tile marked draft shows a DRAFT chip until its number is dropped in.
export const TitleCard: React.FC<{headline: string; tiles: Tile[]}> = ({headline, tiles}) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  const word = ease(frame, 0, fps * 0.8);
  const head = ease(frame, fps * 0.5, fps * 1.3);
  const tileStart = fps * 2.2;
  const tileGap = Math.max(fps * 1.2, (durationInFrames - fps * 4.5 - tileStart) / Math.max(1, tiles.length));
  const accent = [theme.blue, theme.orange, theme.ink];
  return (
    <AbsoluteFill style={{padding: '0 120px', justifyContent: 'center'}}>
      <div style={{display: 'flex', alignItems: 'baseline', gap: 40, opacity: word, transform: `translateY(${(1 - word) * 24}px)`}}>
        <div style={{fontSize: 170, fontWeight: 800, letterSpacing: -6, lineHeight: 1, color: theme.ink}}>scry</div>
        <div style={{display: 'flex', gap: 12, alignSelf: 'center', marginTop: 30}}>
          <div style={{width: 160 * word, height: 14, borderRadius: 7, background: theme.blue}} />
          <div style={{width: 70 * word, height: 14, borderRadius: 7, background: theme.orange}} />
        </div>
      </div>
      <div style={{marginTop: 26, fontSize: 56, color: theme.muted, opacity: head, transform: `translateY(${(1 - head) * 20}px)`}}>
        {headline}
      </div>
      <div style={{display: 'flex', gap: 28, marginTop: 70}}>
        {tiles.map((t, i) => {
          const o = ease(frame, tileStart + i * tileGap, tileStart + i * tileGap + fps * 0.6);
          return (
            <div
              key={i}
              style={{
                flex: 1,
                minWidth: 0,
                background: '#ffffff',
                border: '2px solid #e6e5e1',
                borderTop: `10px solid ${accent[i % accent.length]}`,
                borderRadius: 18,
                padding: '30px 34px 32px',
                boxShadow: '0 10px 30px rgba(0,0,0,0.06)',
                opacity: o,
                transform: `translateY(${(1 - o) * 26}px)`,
                position: 'relative',
              }}
            >
              <div style={{fontSize: 52, fontWeight: 700, lineHeight: 1.15, color: theme.ink, letterSpacing: -1}}>{t.value}</div>
              <div style={{fontSize: 27, lineHeight: 1.3, color: theme.muted, marginTop: 16}}>{t.label}</div>
              {t.draft ? (
                <div
                  style={{
                    position: 'absolute',
                    bottom: 16,
                    right: 18,
                    fontSize: 20,
                    fontWeight: 700,
                    letterSpacing: 1,
                    color: '#fff',
                    background: theme.orange,
                    borderRadius: 8,
                    padding: '4px 10px',
                  }}
                >
                  DRAFT
                </div>
              ) : null}
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
