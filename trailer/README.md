# CampaignFlow trailer

A 2-minute product trailer rendered entirely from code: real app footage, GSAP
motion graphics, an AI voiceover, and a synthesized score. Output:
`docs/videos/campaignflow-trailer.mp4` (1920×1080, 60 fps).

## Story

| Time | Act | What happens |
|---|---|---|
| 0:00 | Hook | "9:47 AM. Three clients. One editor. Four deadlines." Chat messages pile up. |
| 0:08 | Problem | A first-come, first-served queue makes the noon banner 2.5 h late, and a stat card appears (Basis 2025). |
| 0:21 | Turn | "What if your schedule could think?" The logo reveal follows. |
| 0:27 | 01 Check-in | Real footage of the daily review. |
| 0:37 | 02 Plan | An animated min-heap, then greedy allocation, then footage comparing the two priority rules. |
| 0:59 | 03 Lock | Locking in the plan, with confetti. |
| 1:07 | 04 Campaigns | The template pipeline assembles, then a new campaign and a revision round. |
| 1:22 | 05 Safety | DFS catches a loop, then the app's error toast. |
| 1:32 | Impact | 0 late tasks vs 1; 24% less projected lateness; about 2 ms for 250 tasks. All figures are from our own benchmark harness. |
| 1:47 | End | "Stop juggling deadlines. Start shipping." Then credits. |

## How it is built

1. **Narration.** `make_vo.py` reads `script.json`. Each line has a spoken form (`say`) and a caption (`cap`). It generates every line with [Kokoro](https://github.com/thewh1teagle/kokoro-onnx), an open-weight TTS model under Apache 2.0, and writes `build/timeline.json`. Every visual and sound is timed from that file.
2. **Footage.** `record_footage.js` drives the running app and captures Chrome's screencast stream as sharp JPEG frames. It also logs *zoom targets*: element boxes the trailer camera pushes in on.
3. **Picture.** `index.html` and `trailer.js` hold one paused GSAP timeline. `render.js` seeks it frame by frame and pipes screenshots into ffmpeg, so motion is exactly 60 fps however slow the machine is.
4. **Sound.** `mix_audio.py` synthesizes the score and every effect with numpy/scipy, processes the voice, ducks the music under it, and normalizes to −14 LUFS.

## Rebuild

You need Python 3.10+, Node with Playwright (`npm i playwright`), and ffmpeg.

```bash
pip install kokoro-onnx soundfile scipy
```

Download the Kokoro models (`kokoro-v1.0.fp16.onnx` and `voices-v1.0.bin`, about 200 MB) from the [kokoro-onnx releases](https://github.com/thewh1teagle/kokoro-onnx/releases) into a folder. Start the app so the footage can be recorded:

```bash
python -m campaignflow.web.app
```

In a second terminal, build the trailer:

```bash
KOKORO_DIR=/path/to/models bash trailer/build.sh
```

Each step is skipped if its output already exists. Delete the matching file in `build/` to redo just that step.

## Common changes

- **Use a real music track.** Run `bash build.sh --music path/to/track.mp3`. The track replaces the synthesized groove; the hits, whooshes and voice stay. Use music you're licensed to use, for example from Pixabay Music or the YouTube Audio Library.
- **Change a line.** Edit `script.json`, then delete `build/timeline.json` and rebuild. The visuals re-time themselves to the new narration.
- **Use your own voices.** Record each line as `build/vo/<id>.wav` (24 kHz mono), using the line ids in `script.json`. Then update the `dur` values in `build/timeline.json`, or keep each recording close to the AI line's length.
- **Change the voice.** In `script.json`, `"voice"` takes a Kokoro voice name or a weighted blend, e.g. `{"am_puck": 0.6, "am_fenrir": 0.4}`.
- **Preview a moment.** `node render.js --stills 12.5,44` writes stills to `build/stills/`.

Fonts (Inter, JetBrains Mono, SIL OFL) and GSAP (GreenSock standard license, free) are in `vendor/`.
