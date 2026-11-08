"""Edit the events and the music gain keys for each film, then: python score.py v1
Mix voice, the chosen music, Kenney CC0 foley and small synth layers in one room. Times follow voice/timing.json and the comp."""
import glob, json, subprocess, sys
from pathlib import Path
import numpy as np
from scipy import signal
from scipy.io import wavfile

ROOT = Path(__file__).resolve().parent.parent
KEN = ROOT.parent / "onetake-explainer/sfx/kenney"
SR = 48000
DUR = json.load(open(ROOT / "voice/timing.json", encoding="utf8"))["dur"]
N = int(DUR * SR)
rng = np.random.default_rng(55)
T = np.arange(N) / SR


def dec(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).reshape(-1, 2).astype(float)


def fit(x):
    return x[:N] if len(x) >= N else np.vstack([x, np.zeros((N - len(x), 2))])


db = lambda v: 10 ** (v / 20)
sos = lambda kind, f, o=4: signal.butter(o, f, kind, fs=SR, output="sos")
fx = np.zeros((N, 2))


def add(buf, t, gain=0, pan=0):
    i = int(t * SR)
    if i >= N: return
    b = buf[: N - i] * db(gain)
    if b.ndim == 1: b = np.stack([b, b], 1)
    fx[i:i + len(b), 0] += b[:, 0] * (1 - max(pan, 0))
    fx[i:i + len(b), 1] += b[:, 1] * (1 + min(pan, 0))


def ken(name):
    files = sorted(glob.glob(str(KEN / "**" / f"{name}*.ogg"), recursive=True))
    if not files: raise SystemExit(f"no sound {name}")
    return files


def sound(name, i=0):
    f = ken(name); return dec(f[i % len(f)])


def thud(f0=62, dur=.55):
    t = np.arange(int(dur * SR)) / SR
    return np.sin(2 * np.pi * (f0 * t + 30 * (1 - np.exp(-t * 28)) / 28)) * np.exp(-t * 7)


def whoosh(dur, peak=.8, lo=250, hi=5000):
    n = int(dur * SR); x = rng.standard_normal(n); t = np.linspace(0, 1, n)
    env = np.minimum(t / peak, (1 - t) / (1 - peak)) ** 1.7
    out = np.zeros(n); pos = 0
    for k in range(40):                        # a filter sweeping with the camera's speed
        a, b = pos, min(n, pos + n // 40 + 1)
        fc = lo + (hi - lo) * env[(a + b) // 2]
        out[a:b] = signal.sosfilt(sos("low", min(fc, SR / 2 - 100), 2), x)[a:b]
        pos = b
    return out / (np.max(np.abs(out)) + 1e-9) * env


def beep(f, dur=.09):
    t = np.arange(int(dur * SR)) / SR
    return np.sign(np.sin(2 * np.pi * f * t)) * np.exp(-t * 28) * .5


# ------ the picture's events ------
add(thud(), 3.3, -6)
add(sound("impactGlass_light", 1), 3.3, -14)
add(sound("impactGlass_medium", 2), 5.14, -12)
for t, g, p in [(6.9, -24, -.3), (9.1, -26, .25), (11.2, -25, -.1)]:
    add(sound("impactGlass_light", int(t)), t, g, p)
for t, g in [(14.2, -20), (15.4, -18)]:
    add(sound("impactMetal_light", int(t)), t, g)
add(whoosh(1.9, .84), 18.85, -7)                 # the dive through the wall
add(thud(48, .9), 20.7, -5)
add(sound("impactMetal_heavy", 1), 20.7, -13)
add(whoosh(1.35, .8, 400, 7000), 21.8, -9)       # into the corridor
add(sound("impactGeneric_light", 2), 23.1, -13)
add(thud(90, .3), 26.5, -11)
for i, f in enumerate([1320, 990, 1480]):        # the agent's little data chirp before it speaks
    add(beep(f), 26.28 + i * .075, -24)
add(whoosh(4.5, .96, 200, 9000), 29.9, -9)       # the run down the corridor
add(sound("impactGlass_heavy", 0), 34.3, -8)     # through the crack
add(thud(44, 1.1), 34.35, -4)
for i in range(14):                              # fourteen keys
    add(sound("impactMetal_light", i), 36.75 + i * .08, -24, (-1) ** i * .3)
add(thud(50, .8), 40.8, -6)
for i, t in enumerate(np.linspace(43.3, 51.8, 15)):   # windows, far fewer sounds than windows
    add(sound("impactGeneric_light", i), float(t), -24, (-1) ** i * .2)
add(sound("impactGlass_medium", 3), 44.99, -10)  # the face cracks
add(thud(70, .35), 56.92, -10)                   # "test"
for t in (59.3, 60.1, 60.9, 61.7):               # the first pulse comes back: the end meets the start
    add(thud(58, .4), t, -14 if t < 61.5 else -11)

room = np.exp(-np.arange(int(.9 * SR)) / SR * 6.5) * rng.standard_normal(int(.9 * SR))
room = signal.sosfilt(sos("band", [300, 6000], 2), room); room /= np.sqrt(np.sum(room ** 2))
wet = np.stack([signal.fftconvolve(fx[:, c], room)[:N] for c in (0, 1)], 1)
fx = fx + wet * db(-10)

# ------ music shaped to the storyboard ------
music = fit(dec(ROOT / f"music/{sys.argv[1] if len(sys.argv) > 1 else 'v1'}.mp3"))
keys = [(0, -3), (4.2, -3), (5, -13), (12.2, -13), (14, -6), (18.7, -4), (20.8, 0), (21.8, -8), (29.6, -7), (33, -2),
        (40.7, 0), (48.1, 0), (49.3, -6), (54.2, -8), (55.2, -14), (59.1, -22), (DUR, -22)]
gain = np.interp(T, [k[0] for k in keys], [k[1] for k in keys])
music = music * db(gain)[:, None]

voice = fit(dec(ROOT / "voice/voice.wav"))
env = signal.sosfilt(sos("low", 8, 2), np.abs(voice.mean(1)))
env = env / (np.percentile(env, 99) + 1e-9)
duck = 1 - np.clip(env * 1.8, 0, 1) * (1 - db(-10))
music = music * duck[:, None]

mix = voice * db(0) + music * db(-8) + fx * db(-5)
wavfile.write(ROOT / "film/mix-raw.wav", SR, (np.clip(mix, -1, 1) * 32767).astype(np.int16))
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(ROOT / "film/mix-raw.wav"), "-af", "loudnorm=I=-16:TP=-3.5:LRA=11",
                "-ar", "48000", str(ROOT / "film/mix.wav")], check=True)
print("mix done")
