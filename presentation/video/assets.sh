#!/bin/sh
# Copies the committed presentation images into public/img/ so Remotion can serve them with staticFile():
# every PNG of docs/presentation/ plus the frame sequences docs/presentation/session/ (NN.png, the whole session,
# downscaled) and docs/presentation/stages/<read|track|annotate|interpret>/ (NN.png, one overlay set per stage).
# Re-run whenever docs/presentation/ changes; the copies are not committed. Until a sequence is committed,
# placeholders.sh can build it from a run directory (see there).
set -eu
cd "$(dirname "$0")"
src=../../docs/presentation
mkdir -p public/img
cp "$src"/*.png public/img/
for d in session stages; do
  if [ -d "$src/$d" ]; then
    rm -rf "public/img/$d"
    cp -R "$src/$d" "public/img/$d"
    echo "$d: from docs/presentation/$d"
  elif [ -d "public/img/$d" ]; then
    echo "$d: docs/presentation/$d not committed yet; keeping the placeholders in public/img/$d"
  else
    echo "$d: MISSING (run placeholders.sh <run-dir> or commit docs/presentation/$d)"
  fi
done
ls public/img/*.png | wc -l | xargs printf '%s PNGs in public/img\n'
