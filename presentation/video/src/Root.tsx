import React from 'react';
import {Composition, staticFile} from 'remotion';
import {getAudioDurationInSeconds} from '@remotion/media-utils';
import {script, ResolvedScene} from './script';
import {ScryVideo} from './Video';

// Every scene lasts exactly as long as its voice-over file plus script.padSeconds; nothing is hard-coded.
// Scenes marked optional are dropped when their image is not in public/img (see assets.sh).
export const resolveScenes = async (): Promise<ResolvedScene[]> => {
  const scenes: ResolvedScene[] = [];
  let from = 0;
  for (const sc of script.scenes) {
    if (sc.optional && (sc.visual.kind === 'image' || sc.visual.kind === 'frame')) {
      const res = await fetch(staticFile(`img/${sc.visual.src}`), {method: 'HEAD'});
      if (!res.ok) {
        // eslint-disable-next-line no-console
        console.warn(`scene ${sc.id} skipped: img/${sc.visual.src} is missing`);
        continue;
      }
    }
    const voiceSrc = staticFile(`voice/${sc.id}.wav`);
    const voiceSeconds = await getAudioDurationInSeconds(voiceSrc);
    const durationInFrames = Math.ceil((voiceSeconds + script.padSeconds) * script.fps);
    scenes.push({...sc, voiceSrc, voiceSeconds, from, durationInFrames});
    from += durationInFrames;
  }
  return scenes;
};

export const Root: React.FC = () => {
  return (
    <Composition
      id="scry"
      component={ScryVideo}
      width={script.width}
      height={script.height}
      fps={script.fps}
      durationInFrames={script.fps}
      defaultProps={{scenes: [] as ResolvedScene[]}}
      calculateMetadata={async () => {
        const scenes = await resolveScenes();
        const total = scenes.reduce((n, s) => n + s.durationInFrames, 0);
        return {durationInFrames: total, props: {scenes}};
      }}
    />
  );
};
