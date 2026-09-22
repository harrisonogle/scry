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

type Props = {
  heading?: string;
  tiles: Tile[];
  lines?: string[];
  note?: string;
  listHeading?: string;
  list?: string[];
  caption: string;
};

// A statement card: a heading, one or two large tiles that appear in turn, bold lines that follow the voice,
// a small note, and optionally a two-column list revealed item by item (the tiles shrink to make room).
export const CardScene: React.FC<Props> = ({heading, tiles, lines, note, listHeading, list, caption}) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  const head = ease(frame, 0, fps * 0.6);
  const wide = tiles.length === 1;
  const compact = !!(list && list.length);
  const items = list ?? [];
  const perColumn = Math.ceil(items.length / 2);
  const listStart = fps * 2.0;
  const listSpan = Math.max(fps * 3, durationInFrames * 0.55 - listStart);
  return (
    <AbsoluteFill>
      <div
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          top: 0,
          bottom: 120,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: compact ? 'flex-start' : 'center',
          padding: compact ? '44px 100px 0' : '0 120px',
        }}
      >
        {heading ? (
          <div style={{fontSize: 46, color: theme.muted, marginBottom: 54, opacity: head, transform: `translateY(${(1 - head) * 16}px)`}}>{heading}</div>
        ) : null}
        <div style={{display: 'flex', gap: compact ? 28 : 40, justifyContent: 'center', width: '100%'}}>
          {tiles.map((t, i) => {
            const o = ease(frame, fps * (0.4 + i * 0.7), fps * (1.0 + i * 0.7));
            return (
              <div
                key={i}
                style={{
                  width: wide ? 1100 : compact ? 640 : 760,
                  background: '#ffffff',
                  border: '2px solid #e6e5e1',
                  borderTop: `${compact ? 10 : 12}px solid ${accentOf(t, i)}`,
                  borderRadius: 22,
                  padding: compact ? '22px 36px 24px' : '44px 48px 46px',
                  boxShadow: '0 12px 36px rgba(0,0,0,0.07)',
                  opacity: o,
                  transform: `translateY(${(1 - o) * 30}px)`,
                  textAlign: 'center',
                }}
              >
                <div style={{fontSize: compact ? 84 : wide ? 96 : 110, fontWeight: 800, letterSpacing: -3, lineHeight: 1.05, color: accentOf(t, i)}}>{t.value}</div>
                <div style={{fontSize: compact ? 28 : 34, lineHeight: 1.3, color: theme.ink, marginTop: compact ? 10 : 22}}>{t.label}</div>
              </div>
            );
          })}
        </div>
        {note ? (
          <div
            style={{
              marginTop: compact ? 18 : 28,
              fontSize: compact ? 26 : 28,
              color: theme.faint,
              opacity: ease(frame, fps * 1.4, fps * 2.0),
            }}
          >
            {note}
          </div>
        ) : null}
        {(lines ?? []).map((l, i) => {
          const at = fps * (1.8 + i * 1.4);
          const o = ease(frame, at, at + fps * 0.6);
          return (
            <div key={i} style={{marginTop: i === 0 ? 44 : 14, fontSize: 40, fontWeight: 700, color: theme.ink, opacity: o, transform: `translateY(${(1 - o) * 14}px)`}}>
              {l}
            </div>
          );
        })}
        {compact ? (
          <div style={{width: '100%', marginTop: 24}}>
            {listHeading ? (
              <div style={{fontSize: 24, fontWeight: 700, color: theme.muted, letterSpacing: 1, textTransform: 'uppercase', marginBottom: 10, opacity: ease(frame, listStart - fps * 0.4, listStart)}}>
                {listHeading}
              </div>
            ) : null}
            <div style={{display: 'flex', gap: 40}}>
              {[items.slice(0, perColumn), items.slice(perColumn)].map((col, c) => (
                <div key={c} style={{flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: 7}}>
                  {col.map((text, r) => {
                    const i = c * perColumn + r;
                    const at = listStart + (i / Math.max(1, items.length)) * listSpan;
                    const o = ease(frame, at, at + fps * 0.35);
                    return (
                      <div key={r} style={{display: 'flex', gap: 12, fontSize: 22, lineHeight: 1.25, color: theme.ink, opacity: o, transform: `translateX(${(1 - o) * 12}px)`}}>
                        <div style={{flex: '0 0 34px', textAlign: 'right', color: theme.faint, fontVariantNumeric: 'tabular-nums'}}>{i + 1}</div>
                        <div>{text}</div>
                      </div>
                    );
                  })}
                </div>
              ))}
            </div>
          </div>
        ) : null}
      </div>
      <Caption text={caption} />
    </AbsoluteFill>
  );
};
