"""Turn the agent's line into three clearly robotic versions, each also placed inside the narration.

  python robot.py agent/ava-1.mp3
Writes agent/robot-{1,2,3}.wav and agent/context-{1,2,3}.mp3 (the same stretch of take A with the line replaced).
"""
import json, subprocess, sys, pathlib
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt, lfilter

SR = 44100
here = pathlib.Path(__file__).parent
agent = here / "agent"
cfg = json.load(open(here / "config.json", encoding="utf8"))
CUT_IN, CUT_OUT = cfg["cut_in"], cfg["cut_out"]
CTX_IN, CTX_OUT = cfg["context_in"], cfg["context_out"]


def load(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).astype(np.float64)


def band(x, lo, hi):
    return sosfilt(butter(4, [lo, hi], btype="band", fs=SR, output="sos"), x)


def ring(x, hz):
    return x * np.sin(2 * np.pi * hz * np.arange(len(x)) / SR)


def comb(x, ms, fb):
    d = int(SR * ms / 1000)
    a = np.zeros(d + 1); a[0] = 1; a[d] = -fb
    return lfilter([1], a, x)


def crush(x, bits, keep):
    held = np.repeat(x[::keep], keep)[: len(x)]
    q = 2 ** (bits - 1)
    return np.round(held * q) / q


def vocoder(x, pitch, bands=22):
    """A fixed-pitch buzz shaped by the speech: the classic robot."""
    t = np.arange(len(x)) / SR
    carrier = 2 * ((t * pitch) % 1) - 1 + .6 * (2 * ((t * pitch * 1.5) % 1) - 1)
    edges = np.geomspace(140, 7000, bands + 1)
    env_lp = butter(2, 90, fs=SR, output="sos")
    out = np.zeros_like(x)
    for lo, hi in zip(edges[:-1], edges[1:]):
        env = sosfilt(env_lp, np.abs(band(x, lo, hi)))
        out += band(carrier, lo, hi) * np.clip(env, 0, None)
    return out


def norm(x, peak=.85):
    return x / (np.max(np.abs(x)) + 1e-9) * peak


def variants(x):
    # 1 metallic: words stay closest to natural, the tin is obvious
    v1 = .55 * x + .45 * ring(x, 95)
    v1 = comb(v1, 7, .55)
    v1 = band(v1, 180, 6500)
    # 2 machine: ring, comb and a crushed edge
    v2 = .28 * x + .72 * ring(x, 170)
    v2 = comb(v2, 5, .68)
    v2 = crush(band(v2, 220, 5200), 7, 3)
    # 3 synth: fixed-pitch vocoder, the least human, with some source kept so the words hold
    v3 = .82 * norm(vocoder(x, 233)) + .18 * norm(band(x, 1500, 7000))
    return [norm(v) for v in (v1, v2, v3)]


def main():
    src = load(pathlib.Path(sys.argv[1]))
    a = np.argmax(np.abs(src) > .01); b = len(src) - np.argmax(np.abs(src[::-1]) > .01)
    src = src[max(0, a - 400): b + 2000]
    nar = load(here / "narration.mp3")
    level = np.sqrt(np.mean(nar[int(10 * SR):int(20 * SR)] ** 2))
    ramp = lambda n: np.linspace(0, 1, n)
    for i, v in enumerate(variants(src), 1):
        v = v * level / (np.sqrt(np.mean(v[np.abs(v) > .02] ** 2)) + 1e-9) * 1.15
        wavfile.write(agent / f"robot-{i}.wav", SR, (np.clip(v, -1, 1) * 32767).astype(np.int16))
        pre = nar[int(CTX_IN * SR):int(CUT_IN * SR)].copy(); post = nar[int(CUT_OUT * SR):int(CTX_OUT * SR)].copy()
        f = int(.012 * SR); pre[-f:] *= ramp(f)[::-1]; post[:f] *= ramp(f)
        gap = np.zeros(int(.12 * SR))
        ctx = np.concatenate([pre, gap, v, gap, post])
        wav = agent / f"context-{i}.wav"
        wavfile.write(wav, SR, (np.clip(ctx, -1, 1) * 32767).astype(np.int16))
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(wav), "-b:a", "192k", str(agent / f"context-{i}.mp3")], check=True)
        wav.unlink()
        print(i, "line", round(len(v) / SR, 2), "s  context", round(len(ctx) / SR, 2), "s  peak", round(float(np.max(np.abs(ctx))), 3))


main()
