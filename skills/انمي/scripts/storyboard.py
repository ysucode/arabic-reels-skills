"""Check shotlist.json, estimate credits and draw the storyboard page.

Usage: python storyboard.py <project folder>
Writes <project>/storyboard/storyboard.html. Exits 1 when the shot list has errors.
"""
import html
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

W, H = 1080, 1920
SAFE = (200, 270, 880, 1400)  # x0, y0, x1, y1, measured on the user's phone
# Flow prices seen 2026-11-07: Nano Banana 2.1 at 1K costs 305 with one reference and 407 with two or more;
# 2K with two references was 611. Seedance 1.5 Pro 12 s 720p was 1,884 in the app.
PRICE_IMAGE, PRICE_CLIP_12S = 407, 1884
TRIES_IMAGE, TRIES_CLIP = 2, 2
KIND_COLOR = {"seedance": "#e8742c", "panel": "#4c8bf5", "card": "#8a8f98"}


def check(sl):
    errors, warnings = [], []
    shots = sl.get("shots", [])
    total = sl.get("duration", 60)
    t = 0.0
    ids = set()
    for s in shots:
        sid = s.get("id", "?")
        if sid in ids:
            errors.append(f"{sid}: duplicate id")
        ids.add(sid)
        kind = s.get("kind")
        if kind not in KIND_COLOR:
            errors.append(f"{sid}: kind must be seedance, panel or card")
        if abs(s.get("start", -1) - t) > 1e-6:
            errors.append(f"{sid}: starts at {s.get('start')} but the previous shot ends at {t:g}")
        dur = s.get("dur", 0)
        if dur <= 0:
            errors.append(f"{sid}: dur must be positive")
        if kind == "seedance":
            if not (4 <= dur + s.get("media_start", 0) <= 12):
                errors.append(f"{sid}: a Seedance 1.5 clip is 4–12 s; dur + media_start = {dur + s.get('media_start', 0):g}")
            if not s.get("camera"):
                warnings.append(f"{sid}: no camera move")
            if len(s.get("beats", [])) != 3:
                warnings.append(f"{sid}: expected 3 beats (0–4, 4–8, 8–12)")
        if kind == "panel" and dur > 8:
            warnings.append(f"{sid}: a {dur:g} s still may feel slow; split it or add a beat")
        for line in s.get("text", []):
            size = line.get("size", 64)
            half = len(line.get("say", "")) * size * 0.27  # rough Arabic width per character
            x, y = line.get("x", 540), line.get("y", 900)
            if x - half < SAFE[0] or x + half > SAFE[2] or y - size / 2 < SAFE[1] or y + size / 2 > SAFE[3]:
                errors.append(f"{sid}: text «{line.get('say', '')}» leaves the safe zone x200–880, y270–1400")
            if len(line.get("say", "").split()) > 5:
                warnings.append(f"{sid}: «{line.get('say', '')}» has more than 5 words")
            if line.get("t", 0) + line.get("dur", 0) > dur + 1e-6:
                errors.append(f"{sid}: text «{line.get('say', '')}» runs past the shot")
        for fx in s.get("sfx", []):
            if fx.get("t", 0) > dur:
                errors.append(f"{sid}: sfx {fx.get('file')} starts after the shot ends")
        t = s.get("start", t) + dur
    if abs(t - total) > 1e-6:
        errors.append(f"shots end at {t:g} s but duration is {total:g} s")
    return errors, warnings


def budget(sl):
    shots = sl.get("shots", [])
    clips = [s for s in shots if s.get("kind") == "seedance"]
    panels = [s for s in shots if s.get("kind") == "panel"]
    clip_cost = sum(PRICE_CLIP_12S * (s["dur"] + s.get("media_start", 0)) / 12 for s in clips) * TRIES_CLIP
    # Count each distinct picture once: panels often reuse a keyframe or end frame.
    unique = {p for s in clips for p in (s.get("keyframe"), s.get("end_frame")) if p}
    unique |= {s.get("image") for s in panels if s.get("image")}
    images = len(unique) * TRIES_IMAGE
    return {
        "seedance_clips": len(clips),
        "animation_seconds": sum(s["dur"] for s in clips),
        "images_for_frames_and_panels": images,
        "credits_images": images * PRICE_IMAGE,
        "credits_clips": round(clip_cost),
        "credits_total": round(images * PRICE_IMAGE + clip_cost),
        "note": "clip cost assumes price scales with seconds; sheets and the style anchor are extra (about 8 images)",
    }


def frame(s):
    inner = s.get("svg") or ""
    if not inner:
        beats = s.get("beats") or [s.get("note", "")] or [""]
        rows = "".join(
            f"<text x='540' y='{760 + i * 110}' font-size='56' fill='#cfd3da' text-anchor='middle'>{html.escape(b)}</text>"
            for i, b in enumerate(beats) if b)
        inner = rows
    bg = s.get("bg", "#1d2129")
    texts = "".join(
        f"<text x='{l.get('x', 540)}' y='{l.get('y', 900)}' font-size='{l.get('size', 64)}' fill='#fff' "
        f"font-weight='700' text-anchor='middle' dominant-baseline='middle' stroke='#000' stroke-width='3' paint-order='stroke'>"
        f"{html.escape(l.get('say', ''))}</text>" for l in s.get("text", []))
    safe = (f"<rect x='{SAFE[0]}' y='{SAFE[1]}' width='{SAFE[2] - SAFE[0]}' height='{SAFE[3] - SAFE[1]}' "
            "fill='none' stroke='#39d98a' stroke-width='6' stroke-dasharray='24 16'/>")
    return (f"<svg viewBox='0 0 {W} {H}' xmlns='http://www.w3.org/2000/svg'><rect width='{W}' height='{H}' fill='{bg}'/>"
            f"{inner}{texts}{safe}</svg>")


def page(sl, errors, warnings, est):
    total = sl.get("duration", 60)
    bar = "".join(
        f"<div class='seg' style='flex:{s['dur']};background:{KIND_COLOR.get(s.get('kind'), '#555')}' "
        f"title='{s['id']}'>{s['id']}</div>" for s in sl.get("shots", []))
    cards = []
    for s in sl.get("shots", []):
        kind = s.get("kind", "?")
        meta = [f"{s.get('start', 0):g}–{s.get('start', 0) + s.get('dur', 0):g} ث", kind]
        if kind == "seedance":
            meta.append(s.get("camera", ""))
        if kind == "panel":
            meta.append(s.get("move", ""))
        beats = "".join(f"<li>{html.escape(b)}</li>" for b in s.get("beats", []))
        cards.append(
            f"<article><div class='frame'>{frame(s)}</div><h3><span class='dot' style='background:{KIND_COLOR.get(kind, '#555')}'></span>"
            f"{html.escape(s['id'])} · {html.escape(' · '.join(m for m in meta if m))}</h3>"
            f"<p class='vo'>{html.escape(s.get('vo', ''))}</p><ul>{beats}</ul>"
            f"<p class='note'>{html.escape(s.get('note', ''))}</p></article>")
    issues = "".join(f"<li class='err'>{html.escape(e)}</li>" for e in errors) + \
        "".join(f"<li class='warn'>{html.escape(w)}</li>" for w in warnings)
    # Written for the Artifact page contract: the host adds doctype, head and body.
    return f"""<title>{html.escape(sl.get('title', 'ستوريبورد'))}</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Arabic:wght@400;700&display=swap">
<style>
:root{{--bg:#f6f6f4;--fg:#1b1d22;--muted:#5d636e;--card:#fff;--line:#e2e2de}}
@media (prefers-color-scheme:dark){{:root:not([data-theme=light]){{--bg:#121418;--fg:#eceef2;--muted:#9aa1ad;--card:#1b1e24;--line:#2a2e36}}}}
:root[data-theme=dark]{{--bg:#121418;--fg:#eceef2;--muted:#9aa1ad;--card:#1b1e24;--line:#2a2e36}}
@media (prefers-color-scheme:dark){{:root:not([data-theme=light]){{color-scheme:dark}}}} :root[data-theme=dark]{{color-scheme:dark}}
body{{margin:0;background:var(--bg);color:var(--fg);font-family:"IBM Plex Sans Arabic",system-ui,"Segoe UI",Tahoma,sans-serif;padding-block:24px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}}
main{{direction:rtl;max-width:1200px;margin:0 auto}} svg text{{font-family:"IBM Plex Sans Arabic",system-ui,sans-serif}}
h1{{margin:0 0 4px;font-size:24px}} .sub{{color:var(--muted);margin:0 0 16px}}
.bar{{display:flex;direction:ltr;height:28px;border-radius:6px;overflow:hidden;margin-bottom:8px}}
.seg{{color:#fff;font-size:11px;display:flex;align-items:center;justify-content:center;border-left:1px solid #0003;min-width:0;overflow:hidden}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:16px;margin-top:16px}}
article{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px}}
.frame svg{{width:100%;height:auto;border-radius:6px;display:block}}
h3{{font-size:14px;margin:8px 0 4px;display:flex;align-items:center;gap:6px}} .dot{{width:10px;height:10px;border-radius:50%;display:inline-block}}
.vo{{margin:4px 0;font-size:14px}} ul{{margin:4px 0;padding-inline-start:18px;font-size:13px;color:var(--muted)}} .note{{font-size:12px;color:var(--muted);margin:4px 0}}
.issues li.err{{color:#d64545}} .issues li.warn{{color:#b7791f}}
.stats{{display:flex;flex-wrap:wrap;gap:16px;font-size:14px;color:var(--muted)}} .stats b{{color:var(--fg)}}
</style>
<main>
<h1>{html.escape(sl.get('title', 'ستوريبورد'))}</h1>
<p class="sub">{len(sl.get('shots', []))} لقطة · {total:g} ثانية · الإطار الأخضر المتقطع هو منطقة الأمان</p>
<div class="bar">{bar}</div>
<div class="stats"><span>Seedance: <b>{est['seedance_clips']}</b> مقطع، <b>{est['animation_seconds']:g}</b> ث</span>
<span>صور: <b>{est['images_for_frames_and_panels']}</b></span><span>تقدير الكريدت: <b>{est['credits_total']:,}</b> (بدون الشيتات)</span></div>
<ul class="issues">{issues}</ul>
<div class="grid">{''.join(cards)}</div>
</main>"""


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    root = Path(sys.argv[1])
    sl = json.loads((root / "shotlist.json").read_text(encoding="utf-8"))
    errors, warnings = check(sl)
    est = budget(sl)
    out = root / "storyboard" / "storyboard.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(page(sl, errors, warnings, est), encoding="utf-8")
    for e in errors:
        print("ERROR", e)
    for w in warnings:
        print("warn ", w)
    print(json.dumps(est, ensure_ascii=False))
    print("wrote", out)
    sys.exit(1 if errors else 0)


main()
