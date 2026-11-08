#!/bin/bash
# Side-by-side contact sheet so you can *look* at frames (Read the PNG afterwards).
#   bash contact.sh out.png frames/f_0001.png frames/f_0060.png ...   (any number of images)
#   bash contact.sh out.png final.mp4 1 3.5 6 9                       (stills from a video at these seconds)
set -e
OUT="$1"; shift
TMP=$(mktemp -d)
if [[ "$1" == *.mp4 || "$1" == *.mov ]]; then
  VID="$1"; shift; i=0
  for s in "$@"; do ffmpeg -loglevel error -y -ss "$s" -i "$VID" -frames:v 1 "$TMP/$i.png"; i=$((i+1)); done
  set -- "$TMP"/*.png
fi
if [ $# -eq 1 ]; then ffmpeg -loglevel error -y -i "$1" -vf scale=-2:768 "$OUT"; rm -rf "$TMP"; echo "$OUT"; exit 0; fi
ARGS=(); for f in "$@"; do ARGS+=(-i "$f"); done
ffmpeg -loglevel error -y "${ARGS[@]}" -filter_complex "$(for i in $(seq 0 $(($#-1))); do printf "[$i]scale=-2:768[s$i];"; done)$(for i in $(seq 0 $(($#-1))); do printf "[s$i]"; done)hstack=inputs=$#,scale='min(2400,iw)':-2" "$OUT"
rm -rf "$TMP"
echo "$OUT"
