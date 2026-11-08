"""Procedural sound design (no downloads needed): drone, zoom whoosh, impacts, glints, a 'switch on' moment.

  ~/.bpy-venv/bin/python sound.py sound.json out.wav      (needs numpy: the bpy venv already has it)

sound.json (all times in seconds, every key optional except duration):
{
  "duration": 10,
  "whoosh": [[0,0],[0.6,0.25],[3.5,0.45],[5.2,1.0],[5.7,0.5],[8.3,0.15],[10,0]],   # loudness curve
  "whoosh_pitch": [[0,180],[4.6,900],[5.4,2600],[6.5,700],[10,250]],               # centre Hz curve
  "impacts": [5.25],
  "glints": [5.6, 8.0, 14],          # window start, window end, count
  "switch": 8.3,                     # click + electric hum + ticks + bright chord from here
  "seed": 3
}
Output is 48 kHz stereo, peak -1 dBFS. Loudness is normalised later by assemble.py.
"""
import json, sys, wave
import numpy as np

cfg = json.load(open(sys.argv[1])); out = sys.argv[2]
SR = 48000; DUR = float(cfg["duration"]); n = int(SR * DUR); t = np.arange(n) / SR
rng = np.random.default_rng(cfg.get("seed", 3))

def lp(x, fc):
    fc = np.broadcast_to(np.asarray(fc, float), x.shape)
    a = 1 - np.exp(-2 * np.pi * fc / SR); y = np.empty_like(x); s = 0.0
    for i in range(len(x)):
        s += a[i] * (x[i] - s); y[i] = s
    return y
def curve(pts): xs, ys = zip(*pts); return np.interp(t, xs, ys)
def smooth(a, b, x): x = np.clip((x - a) / (b - a), 0, 1); return x * x * (3 - 2 * x)

L = np.zeros(n); R = np.zeros(n)
end_fade = curve([(0, 1), (DUR - 0.7, 1), (DUR, 0)])

# drone
dr = (np.sin(2*np.pi*55*t) + .5*np.sin(2*np.pi*82.4*t + .4) + .25*np.sin(2*np.pi*110.3*t))
dr *= curve([(0, 0), (1, .18), (DUR*.5, .3), (DUR*.8, .38), (DUR, 0)])
L += dr; R += dr * .97

# whoosh
if "whoosh" in cfg:
    fc = curve(cfg.get("whoosh_pitch", [(0, 200), (DUR, 1200)]))
    def band(f):
        w = rng.standard_normal(n); return lp(w, f * 1.6) - lp(w, f / 1.6)
    wl, wr = band(fc), band(fc * 1.04); k = .9 / np.max(np.abs(wl)); e = curve(cfg["whoosh"])
    L += wl * e * k * .55; R += wr * e * k * .55

# impacts (soft sub boom)
for ti in cfg.get("impacts", []):
    m = t >= ti; tb = t[m] - ti
    ph = 2*np.pi*np.cumsum(70*np.exp(-tb*1.5) + 30) / SR
    b = np.sin(ph) * np.exp(-tb*2.2) * .8; L[m] += b; R[m] += b

# metallic glints
if "glints" in cfg:
    g0, g1, cnt = cfg["glints"]
    for _ in range(int(cnt)):
        t0 = rng.uniform(g0, g1); fr = rng.uniform(1800, 4200); pan = rng.uniform(.2, .8)
        m = t >= t0; tt = t[m] - t0
        g = np.sin(2*np.pi*fr*tt)*np.exp(-tt*9)*.05 + np.sin(2*np.pi*fr*2.76*tt)*np.exp(-tt*14)*.02
        L[m] += g*(1-pan); R[m] += g*pan

# switch on
if "switch" in cfg:
    ton = cfg["switch"]; m = t >= ton; tt = t[m] - ton
    ck = rng.standard_normal(m.sum()) * np.exp(-tt*120) * .7; L[m] += ck; R[m] += ck
    hum = (.18*np.sin(2*np.pi*120*t) + .02*np.sign(np.sin(2*np.pi*240*t)) + .06*np.sin(2*np.pi*360*t))
    hum = lp(hum * smooth(ton, ton + .25, t) * end_fade, 1500); L += hum; R += hum
    for i, t0 in enumerate(np.arange(ton + .15, DUR - .1, .085)):
        m = t >= t0; tt = t[m] - t0; pan = .5 + .35*np.sin(i*1.3)
        tk = np.sin(2*np.pi*(5200 + 300*(i % 4))*tt)*np.exp(-tt*60)*.06; L[m] += tk*(1-pan); R[m] += tk*pan
    ch = sum(np.sin(2*np.pi*f0*t) for f0 in (440, 554.4, 659.3, 880)) / 4
    ch *= smooth(ton, ton + .8, t) * end_fade * .12; L += ch; R += ch*.95

st = np.stack([L, R], 1) * curve([(0, 0), (.05, 1), (DUR - .15, 1), (DUR, 0)])[:, None]
st = np.tanh(st * 1.2); st *= 10 ** (-1/20) / np.max(np.abs(st))
with wave.open(out, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((st*32767).astype("<i2").tobytes())
print("wrote", out, f"{DUR:.1f}s")
