"""Set up a new Seedance reel: python new_anime.py <slug> [content-studio path]

Creates <content-studio>/<slug>/ with the stage folders, the templates and the music script from رواية.
"""
import os
import shutil
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
TEMPLATES = SKILL / "assets" / "templates"
RIWAYA_MUSIC = SKILL.parent / "رواية" / "assets" / "music"
DEFAULT_STUDIO = Path(os.environ.get("STUDIO_DIR", str(Path.home() / "content-studio")))
FOLDERS = ["ref", "style", "sheets", "keyframes", "clips", "panels", "voice/takes", "sfx", "storyboard", "export"]


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    studio = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_STUDIO
    root = studio / sys.argv[1]
    if root.exists():
        sys.exit(f"{root} already exists; choose another name")
    for f in FOLDERS:
        (root / f).mkdir(parents=True)
    shutil.copy(TEMPLATES / "style.md", root / "style" / "style.md")
    for name in ("idea.md", "script.md", "shotlist.json"):
        shutil.copy(TEMPLATES / name, root / name)
    if RIWAYA_MUSIC.exists():
        shutil.copytree(RIWAYA_MUSIC, root / "music")
    else:
        (root / "music").mkdir()
        print("warning: رواية music script not found; music/generate.py is missing")
    if not (studio / ".env").exists():
        print(f"warning: {studio / '.env'} not found; music/generate.py needs ELEVENLABS_API_KEY there")
    print(f"ready: {root}")


main()
