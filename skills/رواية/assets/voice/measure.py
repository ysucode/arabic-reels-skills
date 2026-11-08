import json, subprocess, sys, pathlib
from faster_whisper import WhisperModel
sys.stdout.reconfigure(encoding="utf-8")
d = pathlib.Path(sys.argv[1]); m = WhisperModel("small", device="cpu", compute_type="int8"); out = []
total = 0
for f in sorted(d.glob("*.mp3")):
    dur = float(subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",str(f)],capture_output=True,text=True).stdout)
    segs,_ = m.transcribe(str(f), language="ar", word_timestamps=True, initial_prompt=(sys.argv[2] if len(sys.argv) > 2 else "OpenAI, Hugging Face"))
    words = [dict(w=x.word.strip(), s=round(x.start,3), e=round(x.end,3)) for s in segs for x in s.words]
    out.append(dict(file=f.name, dur=round(dur,3), words=words)); total += dur
    print(f.name, f"{dur:.2f}s", " ".join(w["w"] for w in words))
(d/"timing.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8"); print("speech total", round(total,2))
