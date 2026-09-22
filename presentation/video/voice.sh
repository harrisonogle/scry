#!/bin/sh
# Generates one voice-over WAV per scene from script.json into public/voice/<id>.wav.
# Placeholder engine: macOS `say -v Samantha`. To swap the voice, replace the `say` line (or set VOICE_CMD)
# with another engine that writes a WAV (or any format Chromium decodes) to "$out" from "$text",
# then re-run this script and re-render; the scene timings follow the audio durations automatically.
#   VOICE_CMD receives two arguments: the output path and the text.
set -eu
cd "$(dirname "$0")"
mkdir -p public/voice
node -e '
  const s = require("./script.json");
  for (const sc of s.scenes) process.stdout.write(sc.id + "\t" + sc.voice.replace(/\s+/g, " ") + "\n");
' | while IFS="$(printf '\t')" read -r id text; do
  out="public/voice/$id.wav"
  if [ -n "${VOICE_CMD:-}" ]; then
    "$VOICE_CMD" "$out" "$text"
  else
    say -v Samantha -o "$out" --data-format=LEI16@44100 "$text"
  fi
  secs=$(afinfo "$out" 2>/dev/null | awk '/estimated duration/ {print $3}')
  printf '%-24s %6ss  %s\n' "$id" "${secs:-?}" "$out"
done
