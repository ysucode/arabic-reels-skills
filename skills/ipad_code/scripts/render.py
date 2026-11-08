"""Resumable frame renderer for a saved .blend (Cycles, CPU).

  ~/.bpy-venv/bin/python render.py scene.blend --out frames --frames 1-240
  ~/.bpy-venv/bin/python render.py scene.blend --out frames --frames 160,170,180 --pct 100 --samples 28
  ~/.bpy-venv/bin/python render.py scene.blend --out preview --frames 1-240/30 --pct 40 --samples 16

--frames: "a-b", "a-b/step", "a,b,c", or a mix "1-10,50,90-100/5".
Frames that already exist are skipped, and each frame is written to a temp
name and renamed only when complete, so a killed run never leaves a broken
PNG. Re-run the same command to continue.
"""
import argparse, os, sys, time

def parse_frames(spec):
    out = []
    for part in spec.split(","):
        part = part.strip()
        if not part: continue
        step = 1
        if "/" in part: part, step = part.split("/"); step = int(step)
        if "-" in part:
            a, b = map(int, part.split("-")); out += list(range(a, b + 1, step))
        else:
            out.append(int(part))
    return list(dict.fromkeys(out))

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
ap = argparse.ArgumentParser()
ap.add_argument("blend"); ap.add_argument("--out", required=True)
ap.add_argument("--frames", required=True)
ap.add_argument("--pct", type=int, default=None, help="resolution percentage")
ap.add_argument("--samples", type=int, default=None)
a = ap.parse_args(argv)

import bpy
bpy.ops.wm.open_mainfile(filepath=os.path.abspath(a.blend))
s = bpy.context.scene
if a.pct: s.render.resolution_percentage = a.pct
if a.samples: s.cycles.samples = a.samples
s.cycles.device = "CPU"; s.render.threads_mode = "AUTO"
s.render.image_settings.file_format = "PNG"
os.makedirs(a.out, exist_ok=True)

todo = [f for f in parse_frames(a.frames) if not os.path.exists(os.path.join(a.out, f"f_{f:04d}.png"))]
print(f"RENDER {len(todo)} frames to go -> {a.out}", flush=True)
times = []
for i, f in enumerate(todo):
    final = os.path.join(a.out, f"f_{f:04d}.png"); tmp = final + ".part.png"
    t = time.time(); s.frame_set(f); s.render.filepath = tmp
    bpy.ops.render.render(write_still=True)
    os.replace(tmp, final)
    times.append(time.time() - t)
    eta = sum(times) / len(times) * (len(todo) - i - 1) / 60
    print(f"FRAME {f} {times[-1]:.1f}s | {i + 1}/{len(todo)} | ETA {eta:.0f} min", flush=True)
print("RENDER DONE", flush=True)
