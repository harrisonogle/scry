#!/bin/sh
# Copies the committed presentation images into public/img/ so Remotion can serve them with staticFile().
# Re-run whenever docs/presentation/ changes (a redrawn chart, a new image); the copies are not committed.
set -eu
cd "$(dirname "$0")"
mkdir -p public/img
cp ../../docs/presentation/*.png public/img/
ls public/img
