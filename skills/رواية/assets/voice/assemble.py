"""Build the final voice track from narration.mp3, the chosen robot treatment and config.json.
Writes voice.wav, voice.mp3 and timing.json (word times moved onto the final track)."""
import json, subprocess, pathlib
import numpy as np
from scipy.io import wavfile

SR = 44100
here = pathlib.Path(__file__).parent
cfg = json.load(open(here / "config.json", encoding="utf8"))
CUT_IN, CUT_OUT = cfg["cut_in"], cfg["cut_out"]
GAP = cfg["gap"]
HOLD_AT, HOLD = cfg["hold_at"], cfg["hold"]


def load(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).astype(np.float64)


nar, robot = load(here / "narration.mp3"), load(here / f"agent/robot-{cfg['treatment']}.wav")
f = int(.012 * SR); fade = np.linspace(0, 1, f)
def seg(a, b):
    s = nar[int(a * SR):int(b * SR)].copy(); s[:f] *= fade; s[-f:] *= fade[::-1]; return s

gap = np.zeros(int(GAP * SR))
parts = [nar[:int(CUT_IN * SR)] , gap, robot, gap, seg(CUT_OUT, HOLD_AT), np.zeros(int(HOLD * SR)), seg(HOLD_AT, len(nar) / SR), np.zeros(int(.5 * SR))]
parts[0][-f:] *= fade[::-1]
out = np.concatenate(parts)
wavfile.write(here / "voice.wav", SR, (np.clip(out, -1, 1) * 32767).astype(np.int16))
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(here / "voice.wav"), "-b:a", "192k", str(here / "voice.mp3")], check=True)

shift1 = 2 * GAP + len(robot) / SR - (CUT_OUT - CUT_IN)
robot_at = CUT_IN + GAP
def move(t):
    if t < CUT_IN: return t
    if t < HOLD_AT: return t + shift1
    return t + shift1 + HOLD

words = []
for w in json.load(open(here / "narration.json", encoding="utf8"))["words"]:
    if CUT_IN - .2 <= w["s"] < CUT_OUT - .2:
        continue
    words.append(dict(w=w["w"], s=round(move(w["s"]), 3), e=round(move(w["e"]), 3)))
meta = dict(dur=round(len(out) / SR, 3), robot=[round(robot_at, 3), round(robot_at + len(robot) / SR, 3)], words=words)
json.dump(meta, open(here / "timing.json", "w", encoding="utf8"), ensure_ascii=False, indent=1)
print("dur", meta["dur"], "robot", meta["robot"], "shift", round(shift1, 3))
