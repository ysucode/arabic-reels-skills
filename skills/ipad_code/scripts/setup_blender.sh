#!/bin/bash
# Install Blender as a Python module (no GUI) in a cloud session. Safe to run again.
#   bash setup_blender.sh            -> ~/.bpy-venv/bin/python can `import bpy`
# Env: BPY_VENV (default ~/.bpy-venv), BPY_VERSION (default 5.2.3)
set -e
V="${BPY_VENV:-$HOME/.bpy-venv}"
VER="${BPY_VERSION:-5.2.3}"
PY=python3
if ! $PY -c 'import sys; sys.exit(0 if sys.version_info[:2] == (3, 13) else 1)'; then
  echo "note: bpy $VER is built for Python 3.13; found $($PY --version). pip will pick a matching bpy if one exists." >&2
  VER=""
fi
[ -x "$V/bin/python" ] || $PY -m venv "$V"
if ! "$V/bin/python" -c "import bpy" 2>/dev/null; then
  "$V/bin/pip" install -q --disable-pip-version-check "bpy${VER:+==$VER}"
fi
"$V/bin/python" - <<'EOF'
import bpy, os
s = bpy.context.scene
s.render.engine = "CYCLES"
s.cycles.denoiser = "OPENIMAGEDENOISE"
print("Blender", bpy.app.version_string, "| Cycles CPU + OpenImageDenoise OK | cores:", os.cpu_count())
EOF
