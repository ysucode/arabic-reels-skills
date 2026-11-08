"""Generate the section-timed score with Eleven Music. Reads the key from content-studio/.env.

Usage: python generate.py v1 [v2]
"""
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENV = HERE.parent.parent / ".env"

for raw in ENV.read_text(encoding="utf-8-sig").splitlines():
    line = raw.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"'))
KEY = os.environ.get("ELEVENLABS_API_KEY", "")
if not KEY:
    sys.exit("ELEVENLABS_API_KEY is empty in content-studio/.env")

NO_VOICE = ["vocals", "singing", "choir", "spoken words", "humming", "vocal chops"]

DATA = json.loads((HERE / "sections.json").read_text(encoding="utf-8"))
SECTIONS = [(x["ms"], x["styles"], x["avoid"]) for x in DATA["sections"]]
VERSIONS = {k: (v["styles"], v["seed"]) for k, v in DATA["versions"].items()}


def plan(global_styles):
    return {
        "chunks": [
            {
                "text": "",  # text is sung as lyrics, so the section's intent lives only in the styles
                "duration_ms": ms,
                "positive_styles": local + global_styles + ["instrumental", f"{DATA['bpm']} BPM"],
                "negative_styles": avoid + NO_VOICE,
                "context_adherence": "low",
            }
            for ms, local, avoid in SECTIONS
        ]
    }


def generate(version):
    styles, seed = VERSIONS[version]
    body = {"model_id": "music_v2_5", "composition_plan": plan(styles), "seed": seed}
    (HERE / f"{version}.plan.json").write_text(json.dumps(body, ensure_ascii=False, indent=1), encoding="utf-8")
    req = urllib.request.Request(
        "https://api.elevenlabs.io/v1/music?output_format=mp3_44100_192",
        data=json.dumps(body).encode("utf-8"),
        headers={"xi-api-key": KEY, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as res:
            audio = res.read()
            cost = res.headers.get("character-cost") or res.headers.get("x-character-cost")
    except urllib.error.HTTPError as err:
        sys.exit(f"{version}: ElevenLabs error {err.code}: {err.read().decode('utf-8', 'replace')[:700]}")
    out = HERE / f"{version}.mp3"
    out.write_bytes(audio)
    print(f"{out.name}: {len(audio)} bytes, cost header {cost}")


for name in sys.argv[1:]:
    generate(name)
