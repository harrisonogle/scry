// Prints the scene table (start frame and duration of every scene, from the same script.json and voice
// files the composition uses) and renders still PNGs so the look can be checked without playing the video.
//   node stills.mjs                 -> stills/title.png, stills/demo.png, stills/cost-per-video.png
//   node stills.mjs --table         -> the scene table only
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
const composition = await selectComposition({serveUrl, id: 'scry', logLevel: 'error'});
const scenes = composition.props.scenes;
const fps = composition.fps;

console.log(`total ${composition.durationInFrames} frames = ${(composition.durationInFrames / fps).toFixed(2)} s at ${fps} fps`);
console.log('scene                    from   frames   seconds   voice');
for (const s of scenes) {
  console.log(
    `${s.id.padEnd(24)} ${String(s.from).padStart(5)} ${String(s.durationInFrames).padStart(8)} ${(s.durationInFrames / fps).toFixed(2).padStart(9)}   ${s.voiceSeconds.toFixed(2)} s`,
  );
}
fs.mkdirSync(path.join(here, 'out'), {recursive: true});
fs.writeFileSync(path.join(here, 'out/scenes.json'), JSON.stringify({fps, durationInFrames: composition.durationInFrames, scenes}, null, 2));

const args = process.argv.slice(2);
if (args.includes('--table')) process.exit(0);

const wanted = args.length
  ? args.map((a) => {
      const [id, frac] = a.split(':');
      return {id, at: Number(frac ?? 0.5), name: `${id}-${frac ?? '0.5'}`};
    })
  : [
      {id: 'title', at: 0.6, name: 'title'},
      {id: 'demo', at: 0.93, name: 'demo'},
      {id: 'cost-per-video', at: 0.5, name: 'cost-per-video'},
    ];

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
