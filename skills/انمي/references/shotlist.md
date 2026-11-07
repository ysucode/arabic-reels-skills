# shotlist.json

One file drives the storyboard, the credit estimate and the edit. Times are seconds on the final 60 s reel. Paths are relative to the project folder.

```json
{
  "title": "اسم الريل",
  "duration": 60,
  "voice": "voice/voice.wav",
  "music": "music/v1.mp3",
  "music_db": -14,
  "shots": [
    {
      "id": "s01",
      "kind": "seedance",
      "start": 0,
      "dur": 12,
      "camera": "slow dolly in",
      "beats": ["0-4: ...", "4-8: ...", "8-12: ..."],
      "keyframe": "keyframes/s01.png",
      "end_frame": null,
      "clip": "clips/s01.mp4",
      "media_start": 0,
      "vo": "جملة الراوي فوق هذي اللقطة",
      "text": [{"say": "سطر قصير", "t": 0.4, "dur": 2.6, "x": 540, "y": 420, "size": 64}],
      "sfx": [{"file": "sfx/whoosh.mp3", "t": 3.2, "db": -6}],
      "note": "ليش اللقطة موجودة",
      "svg": "<circle cx='540' cy='900' r='160' fill='#f4a340'/>"
    },
    {
      "id": "s02",
      "kind": "panel",
      "start": 12,
      "dur": 4,
      "image": "panels/s02.png",
      "move": "push-in",
      "vo": "...",
      "text": [],
      "sfx": [],
      "svg": ""
    }
  ]
}
```

## Fields

- `kind`: `seedance` (a generated clip), `panel` (a still with a light move) or `card` (plain colour with text only).
- `start`, `dur`: shots are back to back from 0 and add up to `duration`. A Seedance shot uses 4–12 s of its clip; `media_start` trims the clip's head.
- `move` (panels): `push-in`, `pull-out`, `pan-left`, `pan-right`, `drift-up`, `drift-down`, `still`.
- `text[]`: `t` is local to the shot. `x`, `y` are the centre of the line on the 1080×1920 canvas. Every line must sit inside the safe zone x 200–880, y 270–1400; the script estimates the line's width from its length and `size`.
- `sfx[]`: `t` is local to the shot; `db` is gain.
- `svg`: storyboard drawing on a 1080×1920 canvas, inner markup only (no `<svg>` tag). Simple shapes and silhouettes: who is where, which way the camera moves (draw an arrow), where the text sits. Leave it empty and the board shows the beats as text instead.
- `card` shots take `bg` (a hex colour) instead of an image.
