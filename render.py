"""python render.py <scene.blend> <outdir> <pct> <samples> <frames comma list or a-b>"""
import sys, os, time, bpy
blend, out, pct, spp, frames = sys.argv[1:6]
bpy.ops.wm.open_mainfile(filepath=blend)
s = bpy.context.scene
s.render.resolution_percentage = int(pct); s.cycles.samples = int(spp)
s.cycles.device = "CPU"; s.render.threads_mode = "AUTO"
if "-" in frames:
    a, b = map(int, frames.split("-")); fl = range(a, b + 1)
else:
    fl = [int(x) for x in frames.split(",")]
os.makedirs(out, exist_ok=True)
for f in fl:
    p = os.path.join(out, f"f_{f:04d}.png")
    if os.path.exists(p): continue
    t = time.time(); s.frame_set(f); s.render.filepath = p
    bpy.ops.render.render(write_still=True)
    print(f"FRAME {f} {time.time()-t:.1f}s", flush=True)
