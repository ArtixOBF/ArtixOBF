#!/usr/bin/env bash
# Build the CampaignFlow trailer end to end.
#
#   KOKORO_DIR=/path/to/kokoro bash trailer/build.sh [--music track.mp3] [--fps 60] [--jobs 4]
#
# Steps (each is skipped when its output already exists, delete build/ to redo):
#   1. narration     make_vo.py        -> build/vo/*.wav, build/timeline.json
#   2. app footage   record_footage.js -> build/footage/*   (app must run on :5000)
#   3. soundtrack    mix_audio.py      -> build/audio.wav
#   4. picture       render.js x jobs  -> build/part*.mp4 -> build/video.mp4
#   5. final mux                       -> docs/videos/campaignflow-trailer.mp4
set -euo pipefail
cd "$(dirname "$0")"
FPS=60; JOBS=4; MUSIC=""
while [ $# -gt 0 ]; do
  case "$1" in
    --fps) FPS="$2"; shift 2 ;;
    --jobs) JOBS="$2"; shift 2 ;;
    --music) MUSIC="$(realpath "$2")"; shift 2 ;;
    *) echo "unknown option $1"; exit 1 ;;
  esac
done
mkdir -p build

[ -f build/timeline.json ] || python3 make_vo.py
[ -f build/footage/cycle/meta.json ] || node record_footage.js
if [ -n "$MUSIC" ]; then python3 mix_audio.py --music "$MUSIC"; else python3 mix_audio.py; fi

DUR=$(python3 -c "import json; print(json.load(open('build/timeline.json'))['duration'])")
FRAMES=$(python3 -c "print(round($DUR * $FPS))")
echo "rendering $FRAMES frames at $FPS fps in $JOBS parallel jobs"
pids=()
for ((j = 0; j < JOBS; j++)); do
  A=$(python3 -c "print($FRAMES * $j // $JOBS / $FPS)")
  B=$(python3 -c "print($FRAMES * ($j + 1) // $JOBS / $FPS)")
  node render.js --fps "$FPS" --from "$A" --to "$B" --out "build/part$j.mp4" > "build/part$j.log" 2>&1 &
  pids+=($!)
done
for p in "${pids[@]}"; do wait "$p"; done

: > build/parts.txt
for ((j = 0; j < JOBS; j++)); do echo "file 'part$j.mp4'" >> build/parts.txt; done
ffmpeg -y -loglevel error -f concat -safe 0 -i build/parts.txt -c copy build/video.mp4

mkdir -p ../docs/videos
ffmpeg -y -loglevel error -i build/video.mp4 -i build/audio.wav -map 0:v -map 1:a -c:v copy \
  -c:a aac -b:a 256k -shortest -movflags +faststart ../docs/videos/campaignflow-trailer.mp4
echo "wrote docs/videos/campaignflow-trailer.mp4"
