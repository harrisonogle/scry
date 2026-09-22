import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {theme} from '../theme';
import {Caption} from './Caption';
import {Block} from '../script';
import {FADE_FRAMES} from '../theme';

// ---- text model -------------------------------------------------------------------------------

type Style = {
  cite?: 'blue' | 'orange';
  code?: boolean;
  bold?: boolean;
  heading?: boolean;
  dim?: boolean;
  prompt?: boolean;
  name?: boolean;
  marker?: boolean;
};
type SChar = {ch: string; st: Style};
type Row = SChar[];

const COLS = 104;
const LINE_H = 38;
const FONT = 26;

const CITE = /\b(T\d+|L\d+|C\d+|S\d+|\d+:b\d+|frames? \d+(?:[–-]\d+)?|b\d+)\b/g;

const chars = (text: string, st: Style): SChar[] => Array.from(text).map((ch) => ({ch, st}));

// Marks citation ids on an already styled line without touching its other styles.
const markCites = (line: SChar[], orange: Set<string>): SChar[] => {
  const plain = line.map((c) => c.ch).join('');
  const out = line.map((c) => ({...c, st: {...c.st}}));
  for (const m of plain.matchAll(CITE)) {
    const start = m.index ?? 0;
    const colour: 'blue' | 'orange' = orange.has(m[0]) ? 'orange' : 'blue';
    for (let i = start; i < start + m[0].length; i++) {
      if (out[i]) out[i].st.cite = colour;
    }
  }
  return out;
};

// `code`, **bold** and "## heading" as in the recorded answer; the markers themselves are not shown.
const parseMarkdown = (line: string, orange: Set<string>): SChar[] => {
  if (line.startsWith('## ')) return chars(line.slice(3), {heading: true});
  const out: SChar[] = [];
  let code = false;
  let bold = false;
  for (let i = 0; i < line.length; i++) {
    if (line.startsWith('**', i)) {
      bold = !bold;
      i += 1;
      continue;
    }
    if (line[i] === '`') {
      code = !code;
      continue;
    }
    out.push({ch: line[i], st: {code, bold}});
  }
  return markCites(out, orange);
};

// Word-wraps a styled line into rows of at most COLS characters; continuation rows are indented.
const wrap = (line: SChar[], indent: number, cols = COLS): Row[] => {
  const rows: Row[] = [];
  let rest = line;
  let first = true;
  while (rest.length > 0) {
    const pad = first ? 0 : indent;
    const width = cols - pad;
    let cut = rest.length;
    if (rest.length > width) {
      cut = width;
      for (let i = width; i > width * 0.5; i--) {
        if (rest[i].ch === ' ') {
          cut = i;
          break;
        }
      }
    }
    const row = rest.slice(0, cut);
    rows.push(pad ? [...chars(' '.repeat(pad), {}), ...row] : row);
    rest = rest.slice(cut);
    while (rest.length && rest[0].ch === ' ') rest = rest.slice(1);
    first = false;
  }
  if (rows.length === 0) rows.push([]);
  return rows;
};

// ---- timeline ---------------------------------------------------------------------------------
// The scene lasts as long as its voice-over; the animation is laid out as fractions of that span.

// Share of the scene each block takes to appear; what is left (HOLD) keeps the finished transcript on screen.
const weightOf = (b: Block) =>
  b.kind === 'cmd' ? 1.0 : b.kind === 'note' ? 0.5 : b.kind === 'meta' ? 0.3 : b.kind === 'call' ? 0.7 : 2.5;
const DEFAULT_HOLD = 0.18;

const rowsFor = (blocks: Block[], p: number, hold: number, orange: Set<string>): {rows: Row[]; cursor: boolean} => {
  const rows: Row[] = [];
  let cursor = false;
  let t0 = 0;
  const total = blocks.reduce((n, b) => n + weightOf(b), 0);
  for (const block of blocks) {
    const seg = {weight: (weightOf(block) / total) * (1 - hold)};
    const local = Math.min(1, Math.max(0, (p - t0) / seg.weight));
    t0 += seg.weight;
    if (local <= 0) break;
    const done = local >= 1;
    if (block.kind === 'cmd') {
      const line = [...chars('> ', {prompt: true}), ...chars(block.text, {})];
      const budget = done ? line.length : Math.floor(local * line.length);
      for (const row of wrap(line.slice(0, budget), 2)) rows.push(row);
      if (!done) cursor = true;
      else rows.push([]);
    } else if (block.kind === 'meta') {
      rows.push(chars(block.text, {dim: true}));
      rows.push([]);
    } else if (block.kind === 'note') {
      const line = [...chars('⏺ ', {marker: true}), ...chars(block.text, {})];
      const budget = done ? line.length : Math.floor(local * line.length);
      for (const row of wrap(line.slice(0, budget), 2)) rows.push(row);
      if (!done) cursor = true;
      else rows.push([]);
    } else if (block.kind === 'call') {
      rows.push([
        ...chars('⏺ ', {marker: true}),
        ...chars('scry · ', {dim: true}),
        ...chars(block.name, {name: true}),
        ...chars('(' + block.args + ')', {}),
      ]);
      block.results.forEach((r, j) => {
        if (local >= 0.45 + j * 0.2 || done) {
          const body = wrap(markCites(chars(r, {dim: true}), orange), 0, COLS - 5);
          body.forEach((row, k) => rows.push([...chars(j === 0 && k === 0 ? '  ⎿  ' : '     ', {dim: true}), ...row]));
        }
      });
      if (done) rows.push([]);
    } else {
      const lines = block.lines.map((l) => ({
        styled: parseMarkdown(l, orange),
        indent: l.startsWith('    ') ? 4 : 0,
      }));
      const total = lines.reduce((n, l) => n + Math.max(1, l.styled.length), 0);
      let budget = done ? total : Math.floor(local * total);
      for (const l of lines) {
        if (budget <= 0 && !done) break;
        const shown = l.styled.slice(0, budget);
        for (const row of wrap(shown, l.indent)) rows.push(row);
        budget -= Math.max(1, l.styled.length);
      }
      if (!done) cursor = true;
    }
  }
  return {rows, cursor};
};

// ---- rendering --------------------------------------------------------------------------------

const styleFor = (st: Style): React.CSSProperties => {
  const s: React.CSSProperties = {};
  if (st.dim) s.color = theme.termDim;
  if (st.prompt || st.name) {
    s.color = theme.blueLight;
    s.fontWeight = 700;
  }
  if (st.marker) s.color = theme.orange;
  if (st.heading) {
    s.color = theme.orange;
    s.fontWeight = 700;
  }
  if (st.bold) {
    s.fontWeight = 700;
    s.color = '#ffffff';
  }
  if (st.code) {
    s.background = 'rgba(255,255,255,0.09)';
    s.color = '#ffffff';
    s.borderRadius = 4;
  }
  if (st.cite === 'blue') {
    s.background = 'rgba(42,120,214,0.32)';
    s.color = '#d6e7fb';
    s.borderRadius = 4;
  }
  if (st.cite === 'orange') {
    s.background = 'rgba(235,104,52,0.38)';
    s.color = '#ffe0d1';
    s.borderRadius = 4;
    s.fontWeight = 700;
  }
  return s;
};

const sameStyle = (a: Style, b: Style) =>
  a.cite === b.cite &&
  !!a.code === !!b.code &&
  !!a.bold === !!b.bold &&
  !!a.heading === !!b.heading &&
  !!a.dim === !!b.dim &&
  !!a.prompt === !!b.prompt &&
  !!a.name === !!b.name &&
  !!a.marker === !!b.marker;

const RowView: React.FC<{row: Row; cursor?: boolean}> = ({row, cursor}) => {
  const runs: {text: string; st: Style}[] = [];
  for (const c of row) {
    const last = runs[runs.length - 1];
    if (last && sameStyle(last.st, c.st)) last.text += c.ch;
    else runs.push({text: c.ch, st: c.st});
  }
  return (
    <div style={{height: LINE_H, lineHeight: `${LINE_H}px`, whiteSpace: 'pre'}}>
      {runs.map((r, i) => (
        <span key={i} style={styleFor(r.st)}>
          {r.text}
        </span>
      ))}
      {cursor ? (
        <span style={{display: 'inline-block', width: '0.6em', height: '1.05em', background: theme.orange, verticalAlign: 'text-bottom', marginLeft: 2}} />
      ) : null}
    </div>
  );
};

const WIN = {left: 80, top: 36, width: 1760, height: 900, chrome: 52, padX: 30, padY: 22};
const VISIBLE_ROWS = Math.floor((WIN.height - WIN.chrome - WIN.padY * 2) / LINE_H);

type Props = {title: string; status: string; blocks: Block[]; hold?: number; keyCitations?: string[]; caption: string};

export const TerminalScene: React.FC<Props> = ({title, status, blocks, hold, keyCitations, caption}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  // The blocks' shares sum to 1 - hold, so the finished transcript holds for the last `hold` of the scene.
  const p = interpolate(frame, [FADE_FRAMES, durationInFrames - FADE_FRAMES], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const {rows, cursor} = rowsFor(blocks, p, hold ?? DEFAULT_HOLD, new Set(keyCitations ?? []));
  const overflow = Math.max(0, rows.length - VISIBLE_ROWS);
  return (
    <AbsoluteFill>
      <div
        style={{
          position: 'absolute',
          left: WIN.left,
          top: WIN.top,
          width: WIN.width,
          height: WIN.height,
          borderRadius: 18,
          background: theme.termBg,
          boxShadow: '0 20px 60px rgba(0,0,0,0.28)',
          overflow: 'hidden',
          fontFamily: theme.mono,
          fontSize: FONT,
          color: theme.termText,
        }}
      >
        <div
          style={{
            height: WIN.chrome,
            background: theme.termChrome,
            display: 'flex',
            alignItems: 'center',
            padding: '0 22px',
            gap: 10,
            fontFamily: theme.sans,
            fontSize: 20,
            color: '#c7c9cf',
          }}
        >
          <span style={{width: 14, height: 14, borderRadius: 7, background: '#ff5f57'}} />
          <span style={{width: 14, height: 14, borderRadius: 7, background: '#febc2e'}} />
          <span style={{width: 14, height: 14, borderRadius: 7, background: '#28c840'}} />
          <span style={{marginLeft: 16}}>{title}</span>
          <span style={{marginLeft: 'auto', color: '#9aa0a8'}}>{status}</span>
        </div>
        <div style={{position: 'absolute', top: WIN.chrome + WIN.padY, left: WIN.padX, right: WIN.padX, bottom: WIN.padY, overflow: 'hidden'}}>
          <div style={{transform: `translateY(${-overflow * LINE_H}px)`}}>
            {rows.map((row, i) => (
              <RowView key={i} row={row} cursor={cursor && i === rows.length - 1} />
            ))}
          </div>
        </div>
      </div>
      <Caption text={caption} top={WIN.top + WIN.height} />
    </AbsoluteFill>
  );
};
