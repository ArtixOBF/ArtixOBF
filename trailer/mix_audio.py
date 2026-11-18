"""Build the trailer soundtrack: synthesized score + sound effects + voiceover.

Usage:  python trailer/mix_audio.py [--music path/to/track.mp3]

Everything is placed from build/timeline.json (and the footage marks), so
hits and whooshes land on the same frames as the visuals. With --music, the
supplied track replaces the synthesized groove (effects and voice stay).
Writes build/audio.wav (48 kHz stereo, loudness-normalized).
"""

import argparse
import json
import subprocess
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import signal

HERE = Path(__file__).resolve().parent
BUILD = HERE / "build"
SR = 48000
rng = np.random.default_rng(11)

TL = json.loads((BUILD / "timeline.json").read_text())
LINE = {l["id"]: l for l in TL["lines"]}
SC = {s["id"]: s for s in TL["scenes"]}
DUR = TL["duration"] + 0.6
N = int(DUR * SR)
at = lambda i: LINE[i]["start"]
end = lambda i: LINE[i]["start"] + LINE[i]["dur"]


def foot_mark(clip, label):
    meta = json.loads((BUILD / "footage" / clip / "meta.json").read_text())
    return next(m for m in meta["marks"] if m["label"] == label)


# ---------------------------------------------------------------- buses
music = np.zeros((N, 2))
sfx = np.zeros((N, 2))


def put(bus, x, t, gain=1.0, pan=0.0):
    """Mix mono or stereo signal x into bus at time t (seconds)."""
    i = int(t * SR)
    if i >= N or i + len(x) <= 0:
        return
    if x.ndim == 1:
        l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
        x = np.stack([x * l * 1.414, x * r * 1.414], axis=1)
    a, b = max(0, i), min(N, i + len(x))
    bus[a:b] += x[a - i:b - i] * gain


def tt(d):
    return np.arange(int(d * SR)) / SR


def midi(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def sos(kind, f, order=2):
    return signal.butter(order, f, btype=kind, fs=SR, output="sos")


def lp(x, f, order=2):
    return signal.sosfilt(sos("low", min(f, SR / 2.2), order), x, axis=0)


def hp(x, f, order=2):
    return signal.sosfilt(sos("high", f, order), x, axis=0)


def bp(x, lo, hi, order=2):
    return signal.sosfilt(signal.butter(order, [lo, hi], btype="band", fs=SR, output="sos"), x, axis=0)


def sweep_filter(x, f0, f1, kind="low"):
    """Filter with a cutoff that moves exponentially from f0 to f1."""
    out = np.zeros_like(x)
    blocks = max(1, len(x) // 512)
    zi = None
    for k in range(blocks):
        a, b = k * 512, (k + 1) * 512 if k < blocks - 1 else len(x)
        f = f0 * (f1 / f0) ** (k / max(1, blocks - 1))
        s = sos(kind, min(max(f, 20), SR / 2.3))
        if zi is None:
            zi = signal.sosfilt_zi(s) * 0
        out[a:b], zi = signal.sosfilt(s, x[a:b], zi=zi)
    return out


_IR = {}


def reverb(x, secs=2.2, wet=0.35, damp=5000):
    key = (secs, damp)
    if key not in _IR:
        n = int(secs * SR)
        decay = np.exp(-np.arange(n) / SR * (6.9 / secs))
        ir = np.stack([lp(rng.standard_normal(n), damp) * decay, lp(rng.standard_normal(n), damp) * decay], axis=1)
        _IR[key] = ir / np.sqrt((ir ** 2).sum(axis=0))
    ir = _IR[key]
    if x.ndim == 1:
        x = np.stack([x, x], axis=1)
    w = np.stack([signal.fftconvolve(x[:, c], ir[:, c]) for c in range(2)], axis=1)
    dry = np.zeros_like(w)
    dry[: len(x)] = x
    return dry * (1 - wet) + w * wet


# ---------------------------------------------------------------- instruments
def kick(gain=1.0, punch=1.0):
    t = tt(0.5)
    f = 42 + 120 * punch * np.exp(-t * 32)
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) * np.exp(-t * 7.5)
    x[:240] += rng.standard_normal(240) * np.linspace(0.5, 0, 240)   # click
    return np.tanh(x * 1.6) * gain


def clap():
    t = tt(0.25)
    env = np.zeros_like(t)
    for d in (0, 0.011, 0.022):
        env += (t >= d) * np.exp(-(t - d).clip(0) * (90 if d < 0.02 else 18))
    return bp(rng.standard_normal(len(t)), 900, 3200) * env * 1.4


def hat(open_=False):
    t = tt(0.25 if open_ else 0.06)
    return hp(rng.standard_normal(len(t)), 7500) * np.exp(-t * (14 if open_ else 70)) * 0.5


def saw(f, t, detune=0.0):
    return signal.sawtooth(2 * np.pi * f * (1 + detune) * t)


def bass(m, d):
    t = tt(d)
    f = midi(m)
    x = 0.6 * saw(f, t) + 0.5 * np.sin(2 * np.pi * f * t)
    x = lp(x, 520)
    env = np.minimum(1, t / 0.006) * np.exp(-t * 3.0) * np.minimum(1, (d - t) / 0.02)
    return x * env


def pad(notes, d, bright=1400, att=0.5, rel=0.9):
    t = tt(d + rel)
    L = sum(saw(midi(n), t, -0.004) for n in notes)
    R = sum(saw(midi(n), t, 0.004) for n in notes)
    env = np.minimum(1, t / att) * np.where(t > d, np.exp(-(t - d) * 4 / rel), 1)
    x = np.stack([lp(L, bright), lp(R, bright)], axis=1) * env[:, None] / len(notes)
    return x * 0.5


def pluck(m, d=0.35, bright=1.0):
    t = tt(d)
    f = midi(m)
    x = (np.sin(2 * np.pi * f * t) + 0.35 * bright * np.sin(4 * np.pi * f * t) + 0.12 * bright * np.sin(6 * np.pi * f * t))
    return x * np.exp(-t * 11) * np.minimum(1, t / 0.002) * 0.5


def blip(f0=900, f1=1500, d=0.07):
    t = tt(d)
    f = np.linspace(f0, f1, len(t))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 40) * 0.5


def tick():
    t = tt(0.03)
    return (np.sin(2 * np.pi * 3200 * t) + 0.5 * hp(rng.standard_normal(len(t)), 5000)) * np.exp(-t * 180) * 0.35


def impact(size=1.0, tail=1.6):
    t = tt(tail)
    sub = np.sin(2 * np.pi * np.cumsum(38 + 60 * np.exp(-t * 9)) / SR) * np.exp(-t * (2.4 / size))
    noise = lp(rng.standard_normal(len(t)), 2400 + 2500 * size) * np.exp(-t * 7)
    x = np.tanh((sub * 1.3 + noise * 0.6 * size) * 1.4)
    return reverb(x * size, 2.6, 0.3)


def crash(d=2.0):
    t = tt(d)
    x = hp(rng.standard_normal(len(t)), 4000) * np.exp(-t * 2.2) * 0.4
    return reverb(x, 1.8, 0.25)


def whoosh(d=0.6, up=True, gain=1.0):
    t = tt(d)
    n = np.stack([rng.standard_normal(len(t)), rng.standard_normal(len(t))], axis=1)
    f0, f1 = (300, 5000) if up else (5000, 300)
    x = np.stack([sweep_filter(n[:, c], f0, f1, "low") for c in range(2)], axis=1)
    env = np.sin(np.pi * t / d) ** 2
    pan = np.linspace(-0.8, 0.8, len(t))[:, None] * np.array([[-1, 1]])
    return x * env[:, None] * (1 + pan) * 0.5 * gain


def riser(d, gain=1.0):
    t = tt(d)
    n = sweep_filter(rng.standard_normal(len(t)), 200, 9000, "low")
    f = 180 * (6 ** (t / d))
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * (0.5 + 0.5 * np.sin(2 * np.pi * (4 + 18 * t / d) * t))
    env = (t / d) ** 2.2
    return (n * 0.7 + tone * 0.35) * env * gain


def downlifter(d=1.0):
    t = tt(d)
    f = 500 * (0.06 ** (t / d))
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.7 + lp(rng.standard_normal(len(t)), 1500) * 0.3) * np.exp(-t * 2.5) * 0.6


def buzz(d=0.28):
    t = tt(d)
    x = signal.square(2 * np.pi * 110 * t) * 0.5 + signal.square(2 * np.pi * 116 * t) * 0.5
    return lp(x, 1800) * np.exp(-t * 6) * 0.45


def glitch(d=0.5):
    t = tt(d)
    x = rng.standard_normal(len(t))
    gate = (np.floor(t * 38) % 3 != 0).astype(float)
    crushed = np.round(np.sin(2 * np.pi * 220 * t * (1 + 2 * (np.floor(t * 20) % 4))) * 4) / 4
    return (hp(x, 2000) * 0.4 + crushed * 0.5) * gate * np.exp(-t * 4) * 0.6


def sparkle(t0, n=10, base=84):
    for k in range(n):
        put(sfx, pluck(base + [0, 4, 7, 12, 16, 19][k % 6], 0.5), t0 + k * 0.045, 0.22, pan=np.sin(k) * 0.7)


# ---------------------------------------------------------------- score
def build_score(use_groove=True):
    # HOOK: drone + clock + escalating hits
    hk = SC["hook"]
    d = hk["end"] + 0.4
    t = tt(d)
    drone = (np.sin(2 * np.pi * 55 * t) + 0.4 * lp(saw(110, t), 300)) * np.minimum(1, t / 1.5) * np.exp(-np.maximum(0, t - at("h5")) * 3)
    put(music, drone * 0.35, 0)
    k = 0.5
    while k < at("h5") - 0.1:
        put(sfx, tick(), k, 0.55, pan=0.3)
        k += 0.5
    for i, lid in enumerate(["h1", "h2", "h3", "h4"]):
        put(music, kick(1.0, 1.2), at(lid) - 0.02, 0.55 + 0.12 * i)
        put(sfx, impact(0.35 + 0.12 * i, 1.0), at(lid) - 0.02, 0.4)
    b0, b1 = at("h2") - 0.2, at("h5") - 0.35
    for i in range(9):
        put(sfx, blip(800 + 90 * i, 1300 + 90 * i), b0 + (b1 - b0) * (i / 8) ** 0.85 + 0.05, 0.35, pan=((i * 0.37) % 1.6) - 0.8)
    put(sfx, riser(at("h5") - at("h4"), 0.55), at("h4"))
    put(sfx, impact(1.0), at("h5") - 0.08, 0.9)
    put(sfx, glitch(0.6), at("h5") - 0.08, 0.6)
    put(sfx, whoosh(0.5, False, 0.7), hk["end"] - 0.35)

    # PROBLEM: dark pulse in A minor
    pr = SC["problem"]
    beat = 0.5
    t0 = pr["start"] + 0.1
    n = 0
    while t0 + n * beat / 2 < pr["end"] - 0.3:
        tx = t0 + n * beat / 2
        put(music, bass(33, 0.22), tx, 0.5)
        if n % 2 == 0:
            put(music, kick(0.8, 0.7), tx, 0.45)
        if n % 2 == 1:
            put(music, hat(), tx, 0.25, pan=0.4)
        n += 1
    put(music, pad([57, 60, 64], pr["end"] - pr["start"] - 0.6, 900, 1.2, 1.2), pr["start"] + 0.2, 0.55)
    for i in range(3):
        put(sfx, kick(0.6, 0.4), at("p1") + 0.85 + i * 0.55 + 0.55, 0.35)
        put(sfx, whoosh(0.35, True, 0.35), at("p1") + 0.85 + i * 0.55)
    put(sfx, kick(0.7, 0.5), at("p2") + 1.0, 0.4)
    put(sfx, buzz(), at("p2") + 1.0, 0.7)
    put(sfx, tick(), at("p2") + 2.25, 0.8)
    put(sfx, riser(1.0, 0.35), at("p3") + 0.1)
    put(sfx, impact(1.2), at("p3") + 1.1, 1.0)
    put(sfx, glitch(0.5), at("p3") + 1.1, 0.5)
    for k in range(10):   # stat counter ticks
        put(sfx, tick(), end("p3") + 0.45 + 1.3 * (1 - (1 - k / 10) ** 0.5), 0.35)

    # TURN: implode, riser, BIG hit
    tu = SC["turn"]
    put(sfx, downlifter(1.0), tu["start"] - 0.1, 0.8)
    put(sfx, whoosh(0.9, False, 0.8), tu["start"] - 0.1)
    put(sfx, riser(at("t2") - at("t1") + 0.2, 0.9), at("t1") - 0.3)
    hit = at("t2") - 0.08
    put(sfx, impact(1.6, 3.0), hit, 1.0)
    put(sfx, crash(3.0), hit, 0.7)
    put(music, pad([48, 55, 60, 64, 67], tu["end"] - hit - 0.3, 2400, 0.05, 1.5), hit, 0.6)
    sparkle(hit + 0.2, 14, 84)

    # FEATURES + IMPACT: 120 bpm groove, Am F C G
    if use_groove:
        g0, g1 = SC["daily"]["start"], SC["impact"]["end"] - 0.2
        roots = [33, 29, 36, 31]
        chords = [[57, 60, 64], [57, 60, 65], [55, 60, 64], [55, 59, 62]]
        bar = 2.0
        nb = int((g1 - g0) / bar) + 1
        for b in range(nb):
            tb = g0 + b * bar
            if tb >= g1:
                break
            sect = next(s for s in TL["scenes"] if s["start"] <= tb + 0.01 < s["end"] or s is TL["scenes"][-1])
            energy = {"daily": 1, "plan": 2, "lock": 3, "campaign": 3, "cycle": 3, "impact": 4}.get(sect["id"], 2)
            c = b % 4
            put(music, pad(chords[c], bar - 0.05, 1200 + 400 * energy, 0.08, 0.5), tb, 0.32 + 0.04 * energy)
            for q in range(8):   # eighths
                tq = tb + q * 0.25
                if tq >= g1:
                    break
                put(music, bass(roots[c] + (12 if q % 4 == 3 else 0), 0.2), tq, 0.42)
                if q % 2 == 0:
                    put(music, kick(1.0, 1.0), tq, 0.7)
                else:
                    put(music, hat(q == 7), tq, 0.25 + 0.05 * energy, pan=0.35)
                if energy >= 2 and q in (2, 6):
                    put(music, clap(), tq, 0.35)
            if energy >= 2:
                arp = [chords[c][i % 3] + 12 * (1 + (i // 3) % 2) for i in range(16)]
                for i, m in enumerate(arp):
                    put(music, pluck(m, 0.25, 0.6 + 0.1 * energy), tb + i * 0.125, 0.10 + 0.03 * energy, pan=0.5 * np.sin(i * 0.9))
            if energy == 4 and b % 2 == 0:
                put(music, crash(1.5), tb, 0.25)

    # feature transitions + entrances
    feats = ["daily", "plan", "lock", "campaign", "cycle"]
    for i, f in enumerate(feats):
        s = SC[f]
        put(sfx, whoosh(0.55, True, 0.8), s["start"] - 0.25)
        put(sfx, impact(0.5, 1.0), s["start"] + 0.05, 0.35)
    # 01 daily: taps
    put(sfx, tick(), at("d3") + 0.6, 0.9)
    put(sfx, tick(), at("d3") + 2.75, 0.9)
    # 02 plan: click, heap blips, placements, switch stinger
    put(sfx, tick(), at("q1") + 0.6, 0.9)
    items = [(1, 2460, "T2"), (1, 2460, "C4-1"), (1, 2340, "C3-1"), (1, 720, "T3"), (1, 2160, "C2-4"), (0, 660, "T1")]
    arr, steps = [], 0
    for it in items:
        arr.append(it); steps += 1
        i = len(arr) - 1
        while i > 0 and arr[i] < arr[(i - 1) // 2]:
            arr[i], arr[(i - 1) // 2] = arr[(i - 1) // 2], arr[i]; i = (i - 1) // 2; steps += 1
    h0, h1 = at("q2") + 0.05, end("q2") + 1.0
    for k in range(steps):
        put(sfx, blip(700 + 60 * k, 1100 + 60 * k, 0.06), h0 + k * (h1 - h0) / steps, 0.3, pan=np.sin(k) * 0.5)
    put(sfx, pluck(88, 0.6), h1 + 0.05, 0.4)
    p0, p1 = at("q3") + 0.1, end("q3") + 0.4
    for k in range(6):
        put(sfx, whoosh(0.4, True, 0.25), p0 + k * (p1 - p0) / 6)
        put(sfx, pluck([69, 72, 76, 79, 81, 84][k], 0.4), p0 + k * (p1 - p0) / 6 + 0.5, 0.35)
    put(sfx, tick(), at("q4") + 1.35, 0.9)
    put(sfx, buzz(0.4), at("q4") + 2.4, 0.6)
    # 03 lock
    click = at("l1") + 0.9
    put(sfx, tick(), click, 1.0)
    put(sfx, impact(0.9), click + 0.05, 0.8)
    sparkle(click + 0.15, 16, 86)
    # 04 campaign: pipeline pops + revision click
    s = SC["campaign"]
    pt0 = s["start"] + 0.6
    pstep = min(0.32, (at("n1") + LINE["n1"]["dur"] - pt0) / 6)
    for i in range(6):
        put(sfx, pluck([72, 74, 76, 79, 81, 84][i], 0.3), pt0 + i * pstep + 0.05, 0.35)
    put(sfx, tick(), at("n3") + 1.6 + 0.45, 0.9)
    # 05 cycle: DFS ticks, the catch
    s = SC["cycle"]
    tq = s["start"] + 1.0
    for k in range(8):
        put(sfx, blip(1000 + 80 * (k % 4), 1200 + 80 * (k % 4), 0.05), tq + k * 0.2, 0.25)
    for k in range(3):
        put(sfx, blip(900 + 100 * k, 1100 + 100 * k, 0.05), at("c2") + 0.75 + k * 0.22, 0.3)
    put(sfx, impact(1.1), at("c2") + 1.6, 0.9)
    put(sfx, buzz(0.5), at("c2") + 1.6, 0.7)
    put(sfx, glitch(0.4), at("c2") + 1.6, 0.4)

    # IMPACT
    im = SC["impact"]
    put(sfx, whoosh(0.6, True, 0.8), im["start"] - 0.3)
    for lid in ("i1", "i2", "i3"):
        put(sfx, impact(0.7, 1.4), at(lid) - 0.05, 0.6)
    sparkle(at("i1") + 1.05, 10, 84)
    for k in range(24):
        put(sfx, tick(), at("i2") + 0.2 + 1.4 * (1 - (1 - k / 24) ** 0.5), 0.3)
    put(sfx, whoosh(0.5, False, 0.7), im["end"] - 0.4)

    # END
    put(sfx, impact(1.0), at("e1") - 0.04, 0.85)
    put(sfx, impact(1.3), at("e2") - 0.04, 0.95)
    put(sfx, riser(at("e3") - end("e2"), 0.5), end("e2"))
    put(sfx, impact(1.8, 3.5), at("e3") - 0.1, 1.0)
    put(sfx, crash(3.5), at("e3") - 0.1, 0.7)
    sparkle(at("e3"), 16, 84)
    fin = at("e3") - 0.1
    put(music, pad([45, 52, 57, 61, 64, 69], DUR - fin - 1.0, 2600, 0.05, 2.0), fin, 0.7)


# ---------------------------------------------------------------- voice
def build_voice():
    vo = np.zeros(int(DUR * 24000))
    for l in TL["lines"]:
        x, sr = sf.read(BUILD / "vo" / f"{l['id']}.wav")
        i = int(l["start"] * sr)
        vo[i:i + len(x)] += x[: max(0, len(vo) - i)]
    sf.write(BUILD / "vo_raw.wav", vo, 24000)
    chain = ("highpass=f=85,equalizer=f=180:t=q:w=1:g=2,equalizer=f=3200:t=q:w=1.2:g=4,"
             "equalizer=f=9000:t=q:w=1:g=2.5,acompressor=threshold=-20dB:ratio=4:attack=5:release=60:makeup=4,"
             "aresample=48000")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(BUILD / "vo_raw.wav"), "-af", chain,
                    "-ac", "1", str(BUILD / "vo_proc.wav")], check=True)
    v, _ = sf.read(BUILD / "vo_proc.wav")
    v = np.pad(v, (0, max(0, N - len(v))))[:N]
    v = v / (np.abs(v).max() + 1e-9) * 0.9
    room = reverb(v, 0.6, 1.0, 6000)[:N] * 0.06   # a touch of stage room
    return np.stack([v, v], axis=1) + room


def duck_envelope(v, depth=0.6):
    env = np.abs(v[:, 0])
    win = int(0.03 * SR)
    env = np.convolve(env, np.ones(win) / win, mode="same")
    env = np.clip(env / (env.max() + 1e-9) * 6, 0, 1)
    # slow release so the music swells back between lines
    out = np.zeros_like(env)
    g, att, rel = 0.0, 1 - np.exp(-1 / (0.02 * SR)), 1 - np.exp(-1 / (0.35 * SR))
    for k in range(0, len(env), 64):
        target = env[k]
        g += (target - g) * (att if target > g else rel) * 64
        g = min(max(g, 0), 1)
        out[k:k + 64] = g
    return 1 - depth * out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--music", help="optional music track to use instead of the synthesized groove")
    args = ap.parse_args()

    build_score(use_groove=not args.music)
    if args.music:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", args.music, "-ar", str(SR), "-ac", "2",
                        str(BUILD / "music_in.wav")], check=True)
        m, _ = sf.read(BUILD / "music_in.wav")
        m = np.pad(m, ((0, max(0, N - len(m))), (0, 0)))[:N]
        fade = np.ones(N)
        fade[-int(2.5 * SR):] = np.linspace(1, 0, int(2.5 * SR))
        music[:] += m * 0.55 * fade[:, None]

    voice = build_voice()
    duck = duck_envelope(voice, 0.62)[:, None]
    mix = music * 0.55 * duck + sfx * 0.55 * (0.55 + 0.45 * duck) + voice * 1.0
    # gentle master glue, then hand off to loudnorm
    mix = np.tanh(mix * 0.9) / 0.9
    sf.write(BUILD / "mix_raw.wav", mix, SR)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(BUILD / "mix_raw.wav"),
                    "-af", "loudnorm=I=-14:TP=-1.2:LRA=11", "-ar", str(SR), str(BUILD / "audio.wav")], check=True)
    print("wrote", BUILD / "audio.wav", f"({DUR:.1f}s)")


if __name__ == "__main__":
    main()
