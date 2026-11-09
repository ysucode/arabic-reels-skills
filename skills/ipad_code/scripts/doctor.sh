#!/bin/bash
# Report what this session has, as key=value lines. Changes nothing.
#   bash doctor.sh
have() { command -v "$1" >/dev/null 2>&1 && echo yes || echo no; }

echo "where=$([ -n "$CLAUDE_CODE_REMOTE" ] && echo cloud || echo local)"
echo "cores=$(nproc 2>/dev/null || echo "${NUMBER_OF_PROCESSORS:-unknown}")"
echo "ram_gb=$(free -g 2>/dev/null | awk '/^Mem:/{print $2}')"
echo "disk_free=$(df -h . 2>/dev/null | awk 'NR==2{print $4}')"
echo "python=$(python3 --version 2>/dev/null | cut -d' ' -f2)"
echo "ffmpeg=$(have ffmpeg)"
echo "node=$(have node)"

# Launch for real: the library can be present while its browser build is missing.
if NODE_PATH=$(npm root -g 2>/dev/null) node -e "require('playwright').chromium.launch().then(b=>b.close()).catch(()=>process.exit(1))" 2>/dev/null; then pw=yes; else pw=no; fi
echo "playwright=$pw"
[ -x "$HOME/.bpy-venv/bin/python" ] && echo "blender=installed" || echo "blender=not_installed"

url=$(git remote get-url origin 2>/dev/null)
if [ -n "$url" ]; then
  repo=$(echo "$url" | sed -E 's#\.git$##; s#.*[/:]([^/]+/[^/]+)$#\1#')
  echo "repo=$repo"
  echo "branch=$(git branch --show-current 2>/dev/null)"
  code=$(curl -s -o /dev/null -m 10 -w '%{http_code}' -H 'User-Agent: ipad_code' "https://api.github.com/repos/$repo")
  case "$code" in
    200) echo "repo_visibility=public" ;;
    404) echo "repo_visibility=private" ;;
    *)   echo "repo_visibility=unknown" ;;
  esac
else
  echo "repo=none"
fi

SKILL=$(ls -d "$HOME/.claude/skills/ipad_code/SKILL.md" .claude/skills/ipad_code/SKILL.md 2>/dev/null | head -1)
echo "skill=${SKILL:-missing}"
[ -f .claude/ipad_code.json ] && echo "profile=$(tr -d '\n' < .claude/ipad_code.json)" || echo "profile=none"
