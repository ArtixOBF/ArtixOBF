"""Generate the narration with Kokoro and lay out the trailer timeline.

Usage:  KOKORO_DIR=/path/to/models python trailer/make_vo.py

Writes trailer/build/vo/<line>.wav and trailer/build/timeline.json. Every
visual in the trailer is timed from timeline.json, so the picture always
follows the voice.
"""

import json
import os
from pathlib import Path

import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

HERE = Path(__file__).resolve().parent
BUILD = HERE / "build"
SR = 24000


def trim(audio: np.ndarray, thresh: float = 0.01, pad: float = 0.04) -> np.ndarray:
    """Cut leading/trailing silence so line timings are tight."""
    idx = np.where(np.abs(audio) > thresh)[0]
    if not len(idx):
        return audio
    a = max(0, idx[0] - int(pad * SR))
    b = min(len(audio), idx[-1] + int(pad * SR))
    return audio[a:b]


def main() -> None:
    models = Path(os.environ["KOKORO_DIR"])
    model = models / "kokoro-v1.0.fp16.onnx"
    if not model.exists():
        model = models / "kokoro-v1.0.onnx"
    k = Kokoro(str(model), str(models / "voices-v1.0.bin"))
    spec = json.loads((HERE / "script.json").read_text())

    voice = spec["voice"]
    if isinstance(voice, dict):   # weighted blend of voice styles
        voice = sum(w * k.get_voice_style(v) for v, w in voice.items())

    (BUILD / "vo").mkdir(parents=True, exist_ok=True)
    t = 0.0
    timeline = {"scenes": [], "lines": []}
    for scene in spec["scenes"]:
        start = t
        t += scene.get("lead", 0.5)
        lines = []
        for i, line in enumerate(scene["lines"]):
            if i:
                t += scene.get("gap", 0.35)
            t += line.get("pre", 0)
            audio, sr = k.create(line["say"], voice=voice, speed=spec.get("speed", 1.0), lang="en-us")
            assert sr == SR
            audio = trim(audio)
            sf.write(BUILD / "vo" / f"{line['id']}.wav", audio, SR)
            dur = len(audio) / SR
            entry = {"id": line["id"], "scene": scene["id"], "cap": line["cap"],
                     "start": round(t, 3), "dur": round(dur, 3)}
            lines.append(entry)
            timeline["lines"].append(entry)
            t += dur
            print(f"{line['id']:>3} {t - dur:6.2f}s  {dur:4.2f}s  {line['cap']}")
        t += scene.get("tail", 0.5)
        timeline["scenes"].append({"id": scene["id"], "start": round(start, 3),
                                   "end": round(t, 3), "lines": [l["id"] for l in lines]})
    timeline["duration"] = round(t, 3)
    (BUILD / "timeline.json").write_text(json.dumps(timeline, indent=1))
    print(f"total {t:.1f}s")


if __name__ == "__main__":
    main()
