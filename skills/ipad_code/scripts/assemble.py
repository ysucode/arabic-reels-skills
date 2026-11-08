"""Frames + text cards + sound -> final MP4 for Reels/TikTok.

  python3 assemble.py --frames frames --fps 24 --cards cards.json --textdir text --audio sound.wav --out final.mp4
  python3 assemble.py --frames frames --fps 24 --out draft.mp4 --upto 153     (preview of what is rendered so far)

cards.json is the same file text_cards.js uses; each card needs "start" and "end" (seconds).
Cards fade in/out over 0.35 s. Audio is normalised to -14 LUFS, true peak -1.5 dB.
"""
import argparse, json, os, re, subprocess, sys

ap = argparse.ArgumentParser()
ap.add_argument("--frames", required=True); ap.add_argument("--fps", type=float, required=True)
ap.add_argument("--cards"); ap.add_argument("--textdir"); ap.add_argument("--audio")
ap.add_argument("--out", required=True); ap.add_argument("--upto", type=int, help="last frame to include")
ap.add_argument("--crf", type=int, default=16)
a = ap.parse_args()

nums = sorted(int(m.group(1)) for f in os.listdir(a.frames) if (m := re.fullmatch(r"f_(\d+)\.png", f)))
if not nums: sys.exit("no frames found")
first = nums[0]; last = a.upto or nums[-1]
gaps = [f for f in range(first, last + 1) if f not in set(nums)]
if gaps: sys.exit(f"missing frames: {gaps[:20]}{' ...' if len(gaps) > 20 else ''}")
dur = (last - first + 1) / a.fps

cmd = ["ffmpeg", "-loglevel", "error", "-y", "-framerate", str(a.fps), "-start_number", str(first),
       "-i", os.path.join(a.frames, "f_%04d.png")]
inputs = 1; audio_idx = None
if a.audio:
    cmd += ["-i", a.audio]; audio_idx = inputs; inputs += 1
filters = []; last_v = "0:v"
if a.cards:
    cards = json.load(open(a.cards))["cards"]
    for k, c in enumerate(cards):
        if c["start"] >= dur: continue
        cmd += ["-loop", "1", "-framerate", str(a.fps), "-t", f"{dur:.3f}", "-i", os.path.join(a.textdir, f"{c['id']}.png")]
        out_end = max(c["start"] + .4, c["end"])
        filters.append(f"[{inputs}:v]format=rgba,fade=t=in:st={c['start']}:d=0.35:alpha=1,"
                       f"fade=t=out:st={out_end}:d=0.35:alpha=1[c{k}]")
        filters.append(f"[{last_v}][c{k}]overlay=format=auto[v{k}]"); last_v = f"v{k}"; inputs += 1
filters.append(f"[{last_v}]format=yuv420p[vout]")
cmd += ["-filter_complex", ";".join(filters), "-map", "[vout]"]
if audio_idx is not None:
    cmd += ["-map", f"{audio_idx}:a", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "256k", "-ar", "48000"]
cmd += ["-c:v", "libx264", "-preset", "slow", "-crf", str(a.crf), "-profile:v", "high",
        "-movflags", "+faststart", "-t", f"{dur:.3f}", a.out]
subprocess.run(cmd, check=True)
print(f"wrote {a.out}: frames {first}-{last}, {dur:.2f}s")
