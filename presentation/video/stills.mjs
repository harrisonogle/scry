// Prints the scene table (start frame and duration of every scene, from the same script.json and voice
// files the composition uses) and renders still PNGs so the look can be checked without playing the video.
//   node stills.mjs                 -> stills/<id>.png for every scene of the cut that is present
//   node stills.mjs --table         -> the scene table only (every scene of script.json, pending ones included)
// The table and the total always count every scene in script.json, including optional scenes whose image has not
// landed yet (their durations come from the voice WAV headers), and the script exits 1 when the total exceeds
// script.maxSeconds.
//   node stills.mjs <id>:<0..1> ... -> one still per argument, at that fraction of the scene, into stills/<id>-<frac>.png
import {bundle} from '@remotion/bundler';
import {renderStill, selectComposition} from '@remotion/renderer';
import fs from 'node:fs';
import path from 'node:path';

const here = path.dirname(new URL(import.meta.url).pathname);
const serveUrl = await bundle({
  entryPoint: path.join(here, 'src/index.ts'),
  publicDir: path.join(here, 'public'),
  onProgress: () => {},
});
const script = JSON.parse(fs.readFileSync(path.join(here, 'script.json'), 'utf8'));
// If the composition refuses to build (over the ceiling), the table is still printed from the WAV headers.
let composition = null;
try {
  composition = await selectComposition({serveUrl, id: 'scry', logLevel: 'error'});
} catch (err) {
  console.error(`composition refused: ${err.message.split('\n')[0]}`);
}
const scenes = composition ? composition.props.scenes : [];
const fps = composition ? composition.fps : script.fps;

// Seconds of a PCM WAV from its header, for scenes the composition dropped (image not landed yet).
const wavSeconds = (file) => {
  const b = fs.readFileSync(file);
  if (b.toString('ascii', 0, 4) !== 'RIFF' || b.toString('ascii', 8, 12) !== 'WAVE') throw new Error(`${file}: not a WAV`);
  let off = 12;
  let byteRate = 0;
  while (off + 8 <= b.length) {
    const id = b.toString('ascii', off, off + 4);
    const size = b.readUInt32LE(off + 4);
    if (id === 'fmt ') byteRate = b.readUInt32LE(off + 16);
    if (id === 'data') return size / byteRate;
    off += 8 + size + (size % 2);
  }
  throw new Error(`${file}: no data chunk`);
};

// Every scene of script.json, in order: the composition's own numbers where it has the scene, the WAV's otherwise.
let from = 0;
const table = script.scenes.map((sc) => {
  const built = scenes.find((s) => s.id === sc.id);
  const voiceSeconds = built ? built.voiceSeconds : wavSeconds(path.join(here, 'public/voice', `${sc.id}.wav`));
  const durationInFrames = built ? built.durationInFrames : Math.ceil((voiceSeconds + script.padSeconds) * fps);
  const row = {id: sc.id, from, durationInFrames, voiceSeconds, pending: !built, draft: !!sc.draft};
  from += durationInFrames;
  return row;
});
const total = from;
console.log('scene                    from   frames   seconds   voice      ');
for (const s of table) {
  console.log(
    `${s.id.padEnd(24)} ${String(s.from).padStart(5)} ${String(s.durationInFrames).padStart(8)} ${(s.durationInFrames / fps).toFixed(2).padStart(9)}   ${s.voiceSeconds.toFixed(2)} s${s.pending ? '   (pending: image missing, not in the composition)' : ''}${s.draft ? '   DRAFT' : ''}`,
  );
}
console.log(
  `total ${total} frames = ${(total / fps).toFixed(2)} s at ${fps} fps, every scene included (composition now: ${composition ? (composition.durationInFrames / fps).toFixed(2) + ' s' : 'refused'})`,
);
fs.mkdirSync(path.join(here, 'out'), {recursive: true});
fs.writeFileSync(path.join(here, 'out/scenes.json'), JSON.stringify({fps, durationInFrames: total, scenes: table}, null, 2));
if (script.maxSeconds !== undefined && total > script.maxSeconds * fps) {
  console.error(`FAIL: ${(total / fps).toFixed(2)} s exceeds the ${script.maxSeconds} s ceiling (script.maxSeconds, pads included); shorten the voice lines`);
  process.exit(1);
}
console.log(`ok: ${(script.maxSeconds - total / fps).toFixed(2)} s under the ${script.maxSeconds} s ceiling`);

const args = process.argv.slice(2);
if (args.includes('--table')) process.exit(0);
if (!composition) process.exit(1);

const wanted = args.length
  ? args.map((a) => {
      const [id, frac] = a.split(':');
      return {id, at: Number(frac ?? 0.5), name: `${id}-${frac ?? '0.5'}`};
    })
  : [
      {id: 'title', at: 0.9, name: 'title'},
      {id: 'session', at: 0.85, name: 'session'},
      {id: 'demo', at: 0.93, name: 'demo'},
      {id: 'frame', at: 0.95, name: 'frame'},
      {id: 'accuracy', at: 0.8, name: 'accuracy'},
      {id: 'cost', at: 0.8, name: 'cost'},
      {id: 'stages-read', at: 0.5, name: 'stages-read'},
      {id: 'stages-track', at: 0.5, name: 'stages-track'},
      {id: 'stages-annotate', at: 0.5, name: 'stages-annotate'},
      {id: 'stages-interpret', at: 0.5, name: 'stages-interpret'},
      {id: 'hierarchy', at: 0.2, name: 'hierarchy'},
      {id: 'close', at: 0.9, name: 'close'},
    ].filter((w) => {
      const present = scenes.some((s) => s.id === w.id);
      if (!present) console.log(`still ${w.name} skipped: scene ${w.id} is not in the composition (image missing?)`);
      return present;
    });

fs.mkdirSync(path.join(here, 'stills'), {recursive: true});
for (const w of wanted) {
  const sc = scenes.find((s) => s.id === w.id);
  if (!sc) {
    console.error(`no scene ${w.id}`);
    process.exit(1);
  }
  const frame = sc.from + Math.round((sc.durationInFrames - 1) * w.at);
  const output = path.join(here, 'stills', `${w.name}.png`);
  await renderStill({composition, serveUrl, output, frame, imageFormat: 'png', logLevel: 'error'});
  console.log(`${output}  (frame ${frame})`);
}
