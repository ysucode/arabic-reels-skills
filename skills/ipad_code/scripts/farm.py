"""Render farm helper: split frames across cloud sessions and collect what they push.

  python3 farm.py plan    --frames 1-240 --have frames --workers 10
  python3 farm.py precheck --blend scene.blend
  python3 farm.py prompt  --worker 3 --list 162,172,182 --samples 28 --job-branch render-job --out-branch render-out-w03
  python3 farm.py collect --repo . --prefix render-out-w --into frames --frames 1-240

plan     prints, for each worker, the frames still missing from --have, dealt out
         round-robin so the heavy end of the shot is shared evenly.
prompt   prints the exact message to give one worker session (create_session prompt).
collect  fetches every <prefix>NN branch, copies its out/*.png into --into and
         lists the frames that are still missing.
"""
import argparse, os, re, subprocess, sys, tempfile, json

def parse_frames(spec):
    out = []
    for part in spec.split(","):
        part = part.strip()
        if not part: continue
        step = 1
        if "/" in part: part, step = part.split("/"); step = int(step)
        if "-" in part:
            a, b = map(int, part.split("-")); out += list(range(a, b + 1, step))
        else: out.append(int(part))
    return out

def have(d):
    if not d or not os.path.isdir(d): return set()
    return {int(m.group(1)) for f in os.listdir(d) if (m := re.fullmatch(r"f_(\d+)\.png", f))}

WORKER = """You are a render worker. Work autonomously: do not ask questions and do not open a pull request. The repo is checked out on branch `{job}`, which holds `scene.blend`, `render.py` and `setup_blender.sh`. Do not edit them.

1. Install Blender as a Python module: `bash setup_blender.sh` (prints "Blender ... OK").
2. Render, using the Bash tool with run_in_background and the longest timeout, then wait for the completion notice. Do not end your turn while it runs:
   `~/.bpy-venv/bin/python render.py scene.blend --out out --frames {frames} --pct {pct} --samples {samples}`
   If it stops early, run the same command again: finished frames are skipped.
3. Check every frame in the list exists in out/ (f_NNNN.png).
4. Push only the PNGs: `git checkout -b {branch} && git add -f out/*.png && git commit -m "Render frames" && git push -u origin {branch}` (on a network error retry up to 4 times, waiting 2, 4, 8, 16 s).
5. Reply with one line listing the frames you pushed."""

ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
p = sub.add_parser("plan"); p.add_argument("--frames", required=True); p.add_argument("--have"); p.add_argument("--workers", type=int, required=True)
q = sub.add_parser("prompt"); q.add_argument("--worker", type=int, required=True); q.add_argument("--list", required=True)
q.add_argument("--job-branch", default="render-job"); q.add_argument("--out-branch")
q.add_argument("--samples", type=int, required=True, help="same value as the local render"); q.add_argument("--pct", type=int, default=100)
k = sub.add_parser("precheck"); k.add_argument("--blend", required=True)
c = sub.add_parser("collect"); c.add_argument("--repo", default="."); c.add_argument("--prefix", default="render-out-w")
c.add_argument("--into", required=True); c.add_argument("--frames", required=True)
a = ap.parse_args()

if a.cmd == "plan":
    miss = [f for f in parse_frames(a.frames) if f not in have(a.have)]
    plan = {f"w{i + 1:02d}": miss[i::a.workers] for i in range(a.workers)}
    plan = {k: v for k, v in plan.items() if v}
    print(json.dumps({"missing": len(miss), "workers": {k: ",".join(map(str, v)) for k, v in plan.items()}}, indent=1))

elif a.cmd == "prompt":
    br = a.out_branch or f"render-out-w{a.worker:02d}"
    print(WORKER.format(job=a.job_branch, frames=a.list, branch=br, pct=a.pct, samples=a.samples))

elif a.cmd == "precheck":
    mb = os.path.getsize(a.blend) / 1048576
    if mb > 95: sys.exit(f"TOO BIG: {mb:.0f} MB. GitHub refuses files over 100 MB, so reduce textures or geometry first.")
    print(f"OK: {mb:.0f} MB")

elif a.cmd == "collect":
    g = lambda *x: subprocess.run(["git", "-C", a.repo, *x], capture_output=True, text=True)
    refs = [l.split()[1] for l in g("ls-remote", "origin", f"refs/heads/{a.prefix}*").stdout.splitlines()]
    os.makedirs(a.into, exist_ok=True)
    for ref in refs:
        name = ref.removeprefix("refs/heads/")
        r = g("fetch", "-q", "origin", f"{ref}:refs/remotes/origin/{name}")
        if r.returncode: print("fetch failed", name, r.stderr.strip()); continue
        files = [f for f in g("ls-tree", "-r", "--name-only", f"origin/{name}").stdout.split() if re.fullmatch(r"out/f_\d+\.png", f)]
        n = 0
        for f in files:
            dst = os.path.join(a.into, os.path.basename(f))
            if os.path.exists(dst): continue
            blob = subprocess.run(["git", "-C", a.repo, "show", f"origin/{name}:{f}"], capture_output=True).stdout
            with open(dst + ".part", "wb") as fh: fh.write(blob)
            os.replace(dst + ".part", dst); n += 1
        print(f"{name}: {len(files)} frames on branch, {n} new")
    miss = [f for f in parse_frames(a.frames) if f not in have(a.into)]
    print("MISSING", ",".join(map(str, miss)) if miss else "none")
