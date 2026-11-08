"""Set up a new one-take film: python new_film.py <slug> [content-studio path]

Creates <content-studio>/<slug>/ with proto, voice, music, film and vendor, and installs three.js and the render tools.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
ASSETS = SKILL / "assets"
DEFAULT_STUDIO = Path(os.environ.get("STUDIO_DIR", str(Path.home() / "content-studio")))


def run(cmd, cwd, **env):
    subprocess.run(cmd, cwd=cwd, check=True, shell=True, stdout=subprocess.DEVNULL, env={**os.environ, **env})


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    studio = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_STUDIO
    root = studio / sys.argv[1]
    if root.exists():
        sys.exit(f"{root} already exists; choose another name")
    if not (studio / "node_modules/@fontsource/ibm-plex-sans-arabic").exists():
        sys.exit(f"Arabic font not found under {studio}/node_modules; run: npm i @fontsource/ibm-plex-sans-arabic")
    for part in ("proto", "voice", "music", "film"):
        shutil.copytree(ASSETS / part, root / part)
    (root / "voice/takes").mkdir()
    (root / "voice/agent").mkdir()
    vendor = root / "vendor"
    vendor.mkdir()
    (vendor / "three-entry.js").write_text("import * as THREE from 'three';\nwindow.THREE = THREE;\n", encoding="utf-8")
    run("npm init -y", vendor)
    run("npm i three@0.180.0 esbuild@0.25.10 playwright-core sharp --silent --no-audit --no-fund", vendor, PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD="1")
    run("npx esbuild three-entry.js --bundle --format=iife --minify --outfile=three.bundle.js", vendor)
    run("node build.js", root / "proto")
    print(f"ready: {root}")


main()
