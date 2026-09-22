#!/bin/sh
# Generates one voice-over WAV per scene from script.json into public/voice/<id>.wav.
# Engines: VOICE=gemini (default) speaks each line with the Gemini text-to-speech model through voice-gemini.py
# (needs GEMINI_API_KEY in the environment or the repository's .env, and the `outline` extra); VOICE=say uses the
# macOS placeholder `say -v Samantha`; VOICE_CMD=<program> runs any program that writes a WAV to "$out" from "$text".
# Re-run this script and re-render after any change; the scene timings follow the audio durations automatically.
set -eu
cd "$(dirname "$0")"
mkdir -p public/voice
tempo=$(node -e 'console.log(require("./script.json").voiceTempo ?? 1)')
ffmpeg_dir=node_modules/@remotion/compositor-darwin-arm64
node -e '
  const s = require("./script.json");
  for (const sc of s.scenes) process.stdout.write(sc.id + "\t" + sc.voice.replace(/\s+/g, " ") + "\n");
' | while IFS="$(printf '\t')" read -r id text; do
  out="public/voice/$id.wav"
  if [ -n "${VOICE_CMD:-}" ]; then
    "$VOICE_CMD" "$out" "$text"
  elif [ "${VOICE:-gemini}" = "gemini" ]; then
    (cd ../.. && uv run --extra outline python presentation/video/voice-gemini.py "presentation/video/$out" "$text" 2>&1 | grep -v "automatic function calling\|GOOGLE_API_KEY") || exit 1
  else
    say -v Samantha -o "$out" --data-format=LEI16@44100 "$text"
  fi
  if [ "$tempo" != "1" ]; then
    # keep every word, change the pace: Remotion's bundled ffmpeg, atempo keeps the pitch
    DYLD_LIBRARY_PATH="$ffmpeg_dir" "$ffmpeg_dir/ffmpeg" -v error -y -i "$out" -filter:a "atempo=$tempo" "$out.tmp.wav" && mv "$out.tmp.wav" "$out"
  fi
  secs=$(afinfo "$out" 2>/dev/null | awk '/estimated duration/ {print $3}')
  printf '%-24s %6ss  %s\n' "$id" "${secs:-?}" "$out"
done
