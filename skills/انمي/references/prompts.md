# Prompts and settings

Prompts go to the models in English. Replace `<STYLE BLOCK>` and `<CHAR: name>` with the exact lines from `style/style.md`; never paraphrase them between shots.

## Settings

| Job | Model | Aspect | Resolution | Count | Refs (in this order) |
|---|---|---|---|---|---|
| Style anchor | `gemini-nano-banana-2.1` | 9:16 | 2K | 2 | reference frames from `ref/` |
| Face close-up | `gemini-nano-banana-2.1` | 1:1 | 2K | 2 | anchor |
| Character sheet | `gemini-nano-banana-2.1` | 16:9 | 2K | 2 | face, anchor |
| Gadget sheet | `gemini-nano-banana-2.1` | 16:9 | 2K | 2 | anchor (+ face if held) |
| Keyframe | `gemini-nano-banana-2.1` | 9:16 | 2K | 2 | anchor, face, sheet, gadget |
| Panel | `gemini-nano-banana-2.1` | 9:16 | 1K | 2 | anchor, face, sheet |
| Motion | `bytedance-seedance-v1.5-pro` | 9:16 | 720p | 1 | keyframe as `start_frame` (+ `end_frame`) |

Seedance 1.5 Pro parameters (read from the ElevenLabs schema, 2026-11-07): `aspect_ratio` default 16:9, `resolution` 480p or 720p only, `duration_secs` 4–12, `camera_fixed` boolean, `generate_audio` default true. Ports: `prompt`, `start_frame`, `end_frame`. Set `aspect_ratio: "9:16"` and `generate_audio: false` every time. Use `camera_fixed: true` only for a locked-off shot.

Use `gemini-3-pro-image` instead of 2.1 only when a sheet's identity details keep failing.

Say in the prompt what each reference is for. Reference images go in as image parts, in the order of the table.

## Style anchor

```
A single key illustration that defines the visual style of an animated short.
Style: <STYLE BLOCK>.
Scene: <one simple establishing moment from the idea, no main character close-up>.
Vertical 9:16 composition, clear foreground, midground and background.
Match the line quality, shading, palette and lighting of the reference frames; take nothing else from them — no characters, logos or text.
No text, no watermark.
```

## Face close-up (identity)

```
Character design close-up portrait of <CHAR: name>.
Head and shoulders, facing the camera, neutral expression, eyes open, even soft light, plain light grey background.
Style: <STYLE BLOCK>, exactly matching the style reference image.
Crisp detail on eyes, hair and face shape; this image defines the character's identity.
No text.
```

## Character sheet

```
Character turnaround reference sheet of <CHAR: name> on a plain off-white background.
Top row, evenly spaced and aligned to the same height lines: front view, three-quarter view, side view, back view, full body, neutral pose.
Bottom row: four head close-ups showing happy, surprised, scared, determined.
Bottom-right corner: a row of flat colour swatches of the character's palette.
Same face as the face reference image; same rendering style as the style reference image: <STYLE BLOCK>.
Consistent proportions in every view. No labels, no text.
```

## Gadget sheet

```
Prop design reference sheet of <GADGET: description> on a plain off-white background.
Three views: front, three-quarter, side. One view next to a character's hand for scale.
States: closed, open, active (glowing) — side by side.
Rendering style matches the style reference image: <STYLE BLOCK>. No labels, no text.
```

## Keyframe (first frame of a Seedance clip)

```
<shot size and angle>, vertical 9:16 frame.
<CHAR: name> <pose and expression at the first instant>, <position in frame>.
<GADGET if present>. Setting: <place>, <time of day>, light from <source>.
Keep the subject and anything important between 19% and 81% of the frame width and between 14% and 73% of the height (the reel safe zone); leave the top and bottom calm.
Character identity from the face reference and the character sheet; style from the style reference: <STYLE BLOCK>.
No text, no watermark.
```

## Seedance motion prompt

Describe motion only. Camera move first, then one continuous action in three beats, then the consistency line.

```
<camera move: slow dolly in | orbit left | crane up | tracking follow | static>.
0–4s: <action>. 4–8s: <action>. 8–12s: <action and final settle>.
<one atmosphere detail: wind in hair, dust in light, rain>.
Maintain exact appearance from the start frame, consistent character throughout, no deformation, no morphing, no extra limbs, no text, no cuts.
```

With an end frame: write the bridge — "from <start state> to <end state>" — not a static description.

Rules that save credits:
- One camera move per clip; never combine orbit with dolly.
- One main subject, one main action.
- Lighting words beat style adjectives.
- Small natural motion first (breathing, blink, hair) when the clip opens; big action in the middle beat.
- Negative phrases work on Seedance; keep them at the end.

## Sound effects

Use `creative_generate_in_flow` with `eleven_text_to_sound_v2` (no core tool covers SFX). One concrete sound per prompt: "short cartoon whoosh, airy, 0.6 seconds". Free alternative: the Kenney packs already used by رواية.
