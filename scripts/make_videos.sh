#!/usr/bin/env bash
# Convert the raw Playwright recordings to MP4 and join them into one demo.
set -euo pipefail
cd "$(dirname "$0")/../docs/videos"

for f in raw/*.webm; do
  name=$(basename "$f" .webm)
  # Trim the blank first frames, then encode H.264 that plays everywhere.
  ffmpeg -y -loglevel error -ss 0.4 -i "$f" -c:v libx264 -preset slow -crf 24 \
    -pix_fmt yuv420p -r 30 -movflags +faststart -an "$name.mp4"
  echo "wrote $name.mp4"
done

ls 0*.mp4 | sed "s/.*/file '&'/" > concat.txt
ffmpeg -y -loglevel error -f concat -safe 0 -i concat.txt -c copy -movflags +faststart campaignflow-demo.mp4
rm concat.txt
echo "wrote campaignflow-demo.mp4"
