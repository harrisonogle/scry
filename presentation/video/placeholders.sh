#!/bin/sh
# Builds stand-in frame sequences from a scry run directory until the chart agent's versions are committed:
#   public/img/session/NN.png          every decoded frame (frames/000NN.png) downscaled to 1024 px wide
#   public/img/stages/<stage>/NN.png   frames 12 to 31 of the tagged overlay (overlays/000NN.png), 1280 px wide,
#                                      the SAME image for read, track, annotate and interpret (a placeholder)
# Usage: sh placeholders.sh /path/to/runs/v2/grouponly-100
# assets.sh overwrites these as soon as docs/presentation/session and docs/presentation/stages exist.
set -eu
cd "$(dirname "$0")"
run=${1:?run directory}
mkdir -p public/img/session
for f in "$run"/frames/*.png; do
  n=$(basename "$f" .png); nn=$(printf '%02d' "$((10#$n))")
  sips -Z 1024 "$f" --out "public/img/session/$nn.png" >/dev/null
done
for stage in read track annotate interpret; do
  mkdir -p "public/img/stages/$stage"
  i=12
  while [ $i -le 31 ]; do
    nn=$(printf '%02d' $i)
    sips -Z 1280 "$run/overlays/000$nn.png" --out "public/img/stages/$stage/$nn.png" >/dev/null
    i=$((i + 1))
  done
done
echo "placeholders: $(ls public/img/session | wc -l | tr -d ' ') session frames, $(ls public/img/stages/read | wc -l | tr -d ' ') overlay frames x 4 stages"
