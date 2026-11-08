"""Build the HyperFrames edit from shotlist.json.

Usage: python build_edit.py <project folder> [--allow-missing]
Writes <project>/edit/ (index.html, compositions/, package.json, hyperframes.json, assets/). Missing media stops the build
unless --allow-missing, which draws a grey placeholder in their place (for checking timing before generating).
Then: cd <project>/edit && npx --yes hyperframes@0.9.10 check --json

Optional shotlist keys:
- "mix": one finished audio file (voice + music + effects) used instead of voice/music/sfx tracks.
- "screen": {"x0","y0","x1","y1"} the TV screen inside a shared backdrop image, on the 1080x1920 canvas.
- "screen_groups": [{"id","src","shots":[ids],"push":[from,to]}]: consecutive panel shots that share one backdrop
  image become one clip with one continuous camera push; a hand-written HyperFrames scene file (src, relative to the
  project) is mounted over the screen rectangle and moves with the image. Text of those shots is left to the scene.
"""
import os
import html
import json
import re
import shutil
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

W, H = 1080, 1920
HF = "hyperframes@0.9.10"
FONT_DIR = Path(os.environ.get("STUDIO_DIR", str(Path.home() / "content-studio"))) / "node_modules/@fontsource/ibm-plex-sans-arabic/files"
FONTS = {"ar-400.woff2": "ibm-plex-sans-arabic-arabic-400-normal.woff2",
         "ar-700.woff2": "ibm-plex-sans-arabic-arabic-700-normal.woff2",
         "la-400.woff2": "ibm-plex-sans-arabic-latin-400-normal.woff2",
         "la-700.woff2": "ibm-plex-sans-arabic-latin-700-normal.woff2"}
# Panel moves: (from, to) GSAP vars on the image inside the clip.
MOVES = {
    "push-in": ({"scale": 1.0}, {"scale": 1.12}),
    "pull-out": ({"scale": 1.14}, {"scale": 1.0}),
    "pan-left": ({"scale": 1.12, "xPercent": 4}, {"scale": 1.12, "xPercent": -4}),
    "pan-right": ({"scale": 1.12, "xPercent": -4}, {"scale": 1.12, "xPercent": 4}),
    "drift-up": ({"scale": 1.1, "yPercent": 3}, {"scale": 1.1, "yPercent": -3}),
    "drift-down": ({"scale": 1.1, "yPercent": -3}, {"scale": 1.1, "yPercent": 3}),
    "still": ({"scale": 1.0}, {"scale": 1.02}),
}


def gain(db):
    return round(10 ** (db / 20), 4)


def num(x):
    return f"{round(x, 3):g}"


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    root = Path(sys.argv[1]).resolve()
    allow_missing = "--allow-missing" in sys.argv
    sl = json.loads((root / "shotlist.json").read_text(encoding="utf-8"))
    edit = root / "edit"
    assets = edit / "assets"
    (assets / "fonts").mkdir(parents=True, exist_ok=True)
    (edit / "compositions").mkdir(exist_ok=True)
    for dst, src in FONTS.items():
        if (FONT_DIR / src).exists():
            shutil.copy(FONT_DIR / src, assets / "fonts" / dst)
        else:
            print(f"warning: font {src} not found under {FONT_DIR}")

    missing = []

    def bring(rel):
        """Copy a project file into edit/assets and return its asset path, or None when it is missing."""
        if not rel:
            return None
        src = root / rel
        if not src.exists():
            missing.append(rel)
            return None
        dst = assets / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not dst.exists() or dst.stat().st_mtime < src.stat().st_mtime:
            shutil.copy(src, dst)
        return f"assets/{rel}".replace("\\", "/")

    shots = {s["id"]: s for s in sl["shots"]}
    group_of = {}
    for g in sl.get("screen_groups", []):
        for sid in g["shots"]:
            group_of[sid] = g

    body, tweens = [], []
    z = 1
    done_groups = set()
    for s in sl["shots"]:
        sid, start, dur, kind = s["id"], s["start"], s["dur"], s["kind"]
        timing = f'data-start="{num(start)}" data-duration="{num(dur)}" data-track-index="0"'
        g = group_of.get(sid)
        if g:
            if g["id"] in done_groups:
                continue
            done_groups.add(g["id"])
            members = [shots[i] for i in g["shots"]]
            gstart = members[0]["start"]
            gdur = members[-1]["start"] + members[-1]["dur"] - gstart
            src = bring(members[0].get("image"))
            scr = sl["screen"]
            sw, sh = scr["x1"] - scr["x0"], scr["y1"] - scr["y0"]
            scene_src = root / g["src"]
            scene_rel = f"compositions/{g['id']}.html"
            if scene_src.exists():
                shutil.copy(scene_src, edit / scene_rel)
            else:
                missing.append(g["src"])
            img = (f'<img id="i-{g["id"]}" src="{src}" alt="" style="position:absolute;left:0;top:0;width:{W}px;height:{H}px;object-fit:cover">'
                   if src else f'<div id="i-{g["id"]}" class="ph-inner">{g["id"]} · TV</div>')
            host = (f'<div id="{g["id"]}" data-composition-id="{g["id"]}" data-composition-src="{scene_rel}" '
                    f'data-start="{num(gstart)}" data-duration="{num(gdur)}" data-track-index="1" data-track-kind="graphics" '
                    f'data-width="{sw}" data-height="{sh}" '
                    f'style="position:absolute;left:{scr["x0"]}px;top:{scr["y0"]}px;width:{sw}px;height:{sh}px"></div>')
            dim = g.get("dim")  # {"at": reel seconds, "to": opacity, "dur": seconds}: darken the whole frame at the end
            dim_div = (f'<div id="dim-{g["id"]}" style="position:absolute;left:0;top:0;width:{W}px;height:{H}px;background:#05080d;opacity:0"></div>'
                       if dim else "")
            body.append(f'<div id="p-{g["id"]}" class="clip frame" data-start="{num(gstart)}" data-duration="{num(gdur)}" '
                        f'data-track-index="0" data-layout-allow-overflow style="z-index:{z}">'
                        f'<div id="cam-{g["id"]}" class="cam">{img}{host}</div>{dim_div}</div>')
            a, b = g.get("push", [1.0, 1.06])
            tweens.append(f'tl.fromTo("#cam-{g["id"]}", {{scale: {a}}}, {{scale: {b}, duration: {num(gdur)}, ease: "none"}}, {num(gstart)});')
            if dim:
                tweens.append(f'tl.fromTo("#dim-{g["id"]}", {{opacity: 0}}, {{opacity: {dim["to"]}, duration: {num(dim.get("dur", 0.5))}, ease: "power2.out"}}, {num(dim["at"])});')
            z += 1
            continue
        if kind == "seedance":
            src = bring(s.get("clip"))
            if src:
                body.append(
                    f'<video id="v-{sid}" class="clip" {timing} data-media-start="{num(s.get("media_start", 0))}" '
                    f'muted playsinline src="{src}" style="position:absolute;left:0;top:0;width:{W}px;height:{H}px;'
                    f'object-fit:cover;z-index:{z}"></video>')
            else:
                body.append(f'<div id="v-{sid}" class="clip placeholder" {timing} style="z-index:{z}">{html.escape(sid)} · Seedance</div>')
        elif kind == "panel":
            src = bring(s.get("image"))
            inner = (f'<img id="i-{sid}" src="{src}" alt="" style="width:100%;height:100%;object-fit:cover;display:block">'
                     if src else f'<div id="i-{sid}" class="ph-inner">{html.escape(sid)} · panel</div>')
            body.append(f'<div id="p-{sid}" class="clip frame" {timing} data-layout-allow-overflow style="z-index:{z}">{inner}</div>')
            a, b = MOVES.get(s.get("move", "push-in"), MOVES["push-in"])
            tweens.append(f'tl.fromTo("#i-{sid}", {json.dumps(a)}, {{...{json.dumps(b)}, duration: {num(dur)}, ease: "none"}}, {num(start)});')
        else:
            body.append(f'<div id="c-{sid}" class="clip frame" {timing} style="z-index:{z};background:{s.get("bg", "#14161c")}"></div>')
        z += 1

    # Text lines sit above every picture; text of screen-group shots belongs to their scene files.
    for s in sl["shots"]:
        if s["id"] in group_of:
            continue
        for i, line in enumerate(s.get("text", [])):
            tid = f't-{s["id"]}-{i}'
            size = line.get("size", 64)
            x, y = line.get("x", 540), line.get("y", 900)
            st = s["start"] + line.get("t", 0)
            body.append(
                f'<div id="{tid}" class="clip line" data-start="{num(st)}" data-duration="{num(line.get("dur", 2))}" '
                f'data-track-index="2" style="left:{num(x - 340)}px;top:{num(y - size)}px;z-index:100">'
                f'<span id="{tid}-s" style="font-size:{size}px">{html.escape(line.get("say", ""))}</span></div>')
            tweens.append(f'tl.fromTo("#{tid}-s", {{opacity: 0, y: 18}}, {{opacity: 1, y: 0, duration: 0.35, ease: "power3.out"}}, {num(st)});')

    # Sound: one finished mix, or narrator + music + effects as separate tracks.
    audio = []
    total = sl.get("duration", 60)
    mix = bring(sl.get("mix"))
    if mix:
        audio.append(f'<audio id="mix" src="{mix}" data-start="0" data-duration="{num(total)}" data-volume="1" data-track-index="3"></audio>')
    else:
        vo = bring(sl.get("voice"))
        if vo:
            audio.append(f'<audio id="vo" src="{vo}" data-start="{num(sl.get("voice_start", 0))}" data-volume="1" data-track-index="3"></audio>')
        mu = bring(sl.get("music"))
        if mu:
            audio.append(f'<audio id="music" src="{mu}" data-start="0" data-duration="{num(total)}" '
                         f'data-volume="{gain(sl.get("music_db", -14))}" data-fade-out="1.5" data-track-index="4"></audio>')
        n = 0
        for s in sl["shots"]:
            for fx in s.get("sfx", []):
                src = bring(fx.get("file"))
                if src:
                    n += 1
                    audio.append(f'<audio id="fx{n}" src="{src}" data-start="{num(s["start"] + fx.get("t", 0))}" '
                                 f'data-volume="{gain(fx.get("db", 0))}" data-track-index="5"></audio>')

    if missing and not allow_missing:
        for m in missing:
            print("missing:", m)
        sys.exit("media is missing; generate it first, or pass --allow-missing for a timing draft")

    page = f"""<!doctype html>
<html lang="ar" dir="rtl" data-resolution="portrait">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={W}, height={H}" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
    <style>
      @font-face {{ font-family: "Plex Arabic"; font-weight: 700; src: url("assets/fonts/ar-700.woff2") format("woff2"); unicode-range: U+0600-06FF, U+0750-077F, U+FB50-FDFF, U+FE70-FEFF, U+200C-200F; }}
      @font-face {{ font-family: "Plex Arabic"; font-weight: 700; src: url("assets/fonts/la-700.woff2") format("woff2"); unicode-range: U+0000-00FF; }}
      @font-face {{ font-family: "Plex Arabic"; font-weight: 400; src: url("assets/fonts/ar-400.woff2") format("woff2"); unicode-range: U+0600-06FF, U+0750-077F, U+FB50-FDFF, U+FE70-FEFF, U+200C-200F; }}
      @font-face {{ font-family: "Plex Arabic"; font-weight: 400; src: url("assets/fonts/la-400.woff2") format("woff2"); unicode-range: U+0000-00FF; }}
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ width: {W}px; height: {H}px; overflow: hidden; background: #000; }}
      #root {{ position: relative; width: 100%; height: 100%; background: #000; font-family: "Plex Arabic", sans-serif; direction: rtl; }}
      .frame {{ position: absolute; left: 0; top: 0; width: {W}px; height: {H}px; overflow: hidden; }}
      .cam {{ position: absolute; left: 0; top: 0; width: {W}px; height: {H}px; transform-origin: 540px 965px; }}
      .placeholder, .ph-inner {{ position: absolute; left: 0; top: 0; width: {W}px; height: {H}px; background: #3a3f48; color: #cfd3da; font-size: 64px; display: flex; align-items: center; justify-content: center; }}
      .line {{ position: absolute; width: 680px; text-align: center; }}
      .line span {{ display: inline-block; color: #fff; font-weight: 700; line-height: 1.35; text-shadow: 0 4px 18px rgba(0,0,0,.55); }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{num(total)}" data-width="{W}" data-height="{H}">
      {chr(10).join('      ' + b for b in body + audio).strip()}
    </div>
    <script>
      const tl = gsap.timeline({{ paused: true }});
      {chr(10).join('      ' + t for t in tweens).strip()}
      window.__timelines["main"] = tl;
    </script>
  </body>
</html>
"""
    (edit / "index.html").write_text(page, encoding="utf-8")
    name = re.sub(r"[^a-z0-9-]", "", root.name.lower()) or "anime-edit"
    (edit / "package.json").write_text(json.dumps({
        "name": name, "private": True, "type": "module",
        "scripts": {k: f"npx --yes {HF} {k if k != 'dev' else 'preview'}" for k in ("dev", "check", "render")},
    }, indent=2), encoding="utf-8")
    (edit / "hyperframes.json").write_text(json.dumps({
        "$schema": "https://hyperframes.heygen.com/schema/hyperframes.json",
        "paths": {"blocks": "compositions", "components": "compositions/components", "assets": "assets"},
        "media": {"autoProxy": True},
    }, indent=2), encoding="utf-8")
    for m in missing:
        print("placeholder:", m)
    print("wrote", edit / "index.html")


main()
