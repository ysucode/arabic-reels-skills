---
name: ipad_code
description: "اشتغل من الآيباد كأن عندك كمبيوتر قوي: رندر Blender بـ Cycles، ونصوص عربية على الفيديو، وتصميم صوت، وتجميع بـ ffmpeg، ومزرعة رندر من جلسات سحابية متوازية، كلها داخل جلسات Claude Code السحابية بدون PC. استخدمها كلما قال المستخدم ipad_code أو /ipad_code، أو قال إنه على آيباد أو جوال أو ما عنده كمبيوتر، أو طلب مقطع Blender أو رندر ثقيل أو أنيميشن ثلاثي الأبعاد أو تسريع الرندر بأجهزة كثيرة، حتى لو ما ذكر اسم السكل. Use for any heavy creative/compute job (3D render, video, audio) run from an iPad through Claude Code cloud sessions."
---

# ipad_code

المستخدم معه آيباد وClaude Code، وما عنده كمبيوتر. الجلسة السحابية هي الكمبيوتر، والجلسات الإضافية هي مزرعة الرندر. هذا السكل يشرح الطريق اللي جربناه وطلّع مقطع ١٠ ثواني بـ Cycles بدقة 1080×1920 من الصفر للنشر، مع كل مشكلة واجهتنا وحلها.

اكتب للمستخدم بالعربي البسيط. هو على شاشة صغيرة، فخلّ رسائلك قصيرة، وأرسل له الصور والفيديو بـ `SendUserFile` بدل ما توصفها.

`$SK` في هذا الملف يعني مجلد السكل (المجلد اللي فيه هذا الملف). أول شي حدده:

```bash
SK=$(dirname "$(ls -d ~/.claude/skills/ipad_code/SKILL.md .claude/skills/ipad_code/SKILL.md 2>/dev/null | head -1)")
```

## 0. التجهيز لأول مرة (على الآيباد)

اشرح هذي للمستخدم إذا كانت أول مرة له، خطوة وحدة كل مرة:

1. يفتح Claude Code من تطبيق Claude أو من `claude.ai/code` في Safari، ويربط حسابه في GitHub لما يطلبه.
2. يسوي مستودع في GitHub من Safari (ولو فاضي فيه README بس). الجلسات السحابية تشتغل على مستودع، والمزرعة تنقل الإطارات عن طريقه.
3. **تركيب السكل:** ما فيه `~/.claude` دائم على الآيباد، فالسكل لازم يكون داخل المستودع. اطلب من Claude في جلسة على مستودعه: «انسخ مجلد `skills/ipad_code` من `ysucode/arabic-reels-skills` إلى `.claude/skills/ipad_code` في هذا المستودع وارفعه». بعدها كل جلسة جديدة على المستودع تشوف السكل.
4. يبدأ جلسة جديدة على المستودع ويطلب اللي يبيه.

## 1. وش عندك في الجلسة السحابية

قِس، لا تفترض: `nproc; free -g; df -h .; python3 --version; which ffmpeg node`.

اللي لقيناه: ٤ أنوية CPU، و١٥ جيجا رام، وبدون كرت شاشة، وPython 3.13، وffmpeg، وNode، وChromium مع Playwright جاهزين. حزم pip وnpm تنزل عادي، وخطوط Google Fonts توصل. **Blender مو موجود**، والحل تحت.

| اللي يسويه الكمبيوتر عادة | البديل في الجلسة | السكربت |
|---|---|---|
| Blender (برنامج) | Blender كمكتبة Python من pip (`bpy`) بدون واجهة، ورندر Cycles على CPU مع OpenImageDenoise | `setup_blender.sh`، `render.py` |
| معاينة الشغل بالعين | صفحة مصغّرات من إطارات أو من الفيديو، ثم تقرأها كصورة وترسلها للمستخدم | `contact.sh` |
| After Effects (نص عربي على الفيديو) | Chromium يرسم النص بخط Cairo من Google Fonts بتشكيل عربي صحيح، كصور PNG شفافة | `text_cards.js` |
| مكتبة مؤثرات صوتية | صوت مولّد بالكود: هدير، وwhoosh يتبع الزوم، وصدمات، ولمعات، ولحظة «تشغيل» | `sound.py` |
| Premiere (تجميع وتصدير) | ffmpeg: إطارات، ونصوص بتلاشي، وصوت بمستوى ‎-14 LUFS، وH.264 | `assemble.py` |
| جهاز رندر قوي | مزرعة رندر: جلسات سحابية متوازية، كل وحدة ٤ أنوية | `farm.py` + [references/farm.md](references/farm.md) |
| صوت راوي وموسيقى | ElevenLabs عن طريق الـ MCP (شوف سكل `نبرة`). تنزيل الملف يحتاج السماح للـ host، والتفاصيل في [references/pitfalls.md](references/pitfalls.md) | |
| تسليم الملف | `SendUserFile` يطلع بطاقة في التطبيق، ومنها يحفظ المستخدم الفيديو في الصور | |

## 2. ابنِ المشروع

```bash
bash $SK/scripts/setup_blender.sh          # ~30 ثانية، يطبع: Blender 5.2.3 ... OK
P=<مجلد المشروع داخل scratchpad>
~/.bpy-venv/bin/python <build.py> $P       # يكتب $P/scene.blend
```

- المشهد يُبنى بسكربت Python (`build.py`) يكتب `scene.blend`. مثال كامل ومجرب: [assets/examples/transistor/build.py](assets/examples/transistor/build.py) (زوم من معالج على اللوحة الأم لين ترانزستور FinFET)، وفيه حلول لمشاكل الزوم الكبير: الكاميرا بمسافة لوغاريتمية، و`clip_start` يتغير مع المسافة، وسطح يذوب بالـ Alpha، و«وادي» مقصوص يمر فيه الكاميرا بدون ما تصدم شي.
- عمودي للريلز: 1080×1920، و24 إطار بالثانية. 24 تكفي وتوفّر ٢٠٪ من الرندر مقارنة بـ 30.
- الإعدادات اللي نجحت: Cycles على CPU، وadaptive sampling، وOpenImageDenoise، وAgX، وmotion blur خفيف، و`use_persistent_data`.
- خلّ الإضاءة كلها شمس (Sun) للمشاهد اللي حجمها يتغير كثير، لأن الشمس ما تتأثر بالمسافة. وحط أضواء نقطية صغيرة للتفاصيل.
- **الانبعاث (Emission) يحترق بسرعة** مع AgX. ابدأ بقيمة بين 0.5 و1.5.

## 3. شوف قبل ما ترندر (بوابة)

```bash
~/.bpy-venv/bin/python $SK/scripts/render.py $P/scene.blend --out $P/preview --frames 1-240/30 --pct 40 --samples 24
bash $SK/scripts/contact.sh $P/contact.png $P/preview/f_*.png
```

اقرأ `contact.png` بنفسك، ثم أرسله للمستخدم. صلّح اللي تشوفه (إضاءة محترقة، كاميرا تصدم، لقطة فاضية)، وأعد البناء. **لا ترندر الكامل قبل موافقة المستخدم على المعاينة.**

## 4. احسب الوقت وقرر

رندر أثقل إطار (عادة آخر المقطع) بالدقة والجودة النهائية:

```bash
~/.bpy-venv/bin/python $SK/scripts/render.py $P/scene.blend --out $P/timing --frames 175,240 --pct 100 --samples 28
```

الوقت الكلي تقريباً = عدد الإطارات × 0.75 × وقت أثقل إطار. في تجربتنا كان أثقل إطار ١٠٠ إلى ١٥٠ ثانية، يعني ٢٤٠ إطار ≈ ٧ ساعات على جهاز واحد.

- **أقل من ٩٠ دقيقة:** ارندر هنا في الخلفية (الخطوة 5).
- **أكثر من كذا:** اقترح المزرعة (الخطوة 6). قل للمستخدم كم جهاز، وكم ياخذ الوقت، وإن كل جهاز يستهلك من حد استخدامه (تقريباً نص دولار من التوكنز لكل جهاز في تجربتنا)، وإن الإطارات بتنرفع على فروع مؤقتة في مستودعه هو لازم يحذفها بنفسه. **ابدأ المزرعة بس بعد موافقته وعدد الأجهزة اللي يحدده.**

## 5. رندر محلي

```bash
~/.bpy-venv/bin/python $SK/scripts/render.py $P/scene.blend --out $P/frames --frames 1-240 --pct 100 --samples 28 >> $P/render.log 2>&1
```

- شغّله بأداة Bash مع `run_in_background` والـ timeout الأقصى. **لا تستخدم `&`**، لأن العملية تموت بين الأوامر.
- الأمر في الخلفية يوقف بعد ساعتين، وبعدها ما يحق لك تعيد تشغيله من نفسك. عشان كذا قسّم الرندر لدفعات كل وحدة أقل من ٩٠ دقيقة (مثلاً `--frames 1-120` ثم `121-240`). السكربت يتخطى الإطارات الجاهزة، فإعادة نفس الأمر تكمّل من وين وقف.
- تابع التقدم من `render.log`، وفيه ETA لكل إطار.

## 6. مزرعة الرندر (أجهزة كثيرة)

الخطوات بالتفصيل في [references/farm.md](references/farm.md). باختصار:

1. ارفع `scene.blend` و`render.py` و`setup_blender.sh` على فرع وظيفة (orphan) اسمه `render-job`.
2. `python3 $SK/scripts/farm.py plan --frames 1-240 --have $P/frames --workers N` يوزّع الإطارات الناقصة بالتناوب، عشان الإطارات الثقيلة تنقسم بالتساوي.
3. لكل جهاز: `create_session` على المستودع، و`source_revision: render-job`، و`outcome_branch: render-out-wNN`، والـ prompt من `farm.py prompt`.
4. الجلسة اللي تخلص ما ترجع تبلغك. جدول لنفسك فحص بـ `send_later` بعد ٢٥ إلى ٣٠ دقيقة، وشيّك بـ `get_session` وبـ `farm.py collect`.
5. أي جهاز وقف بدون ما يرفع شي: أرسل له `send_message` يكمّل. وفي نفس الوقت ارندر إطاراته الناقصة هنا من الآخر للأول، واللي يخلص أول تاخذ منه.
6. بعد ما تكتمل الإطارات، أرشف الجلسات بـ `archive_session`. وقل للمستخدم يحذف فروع `render-job` و`render-out-w*` من صفحة Branches في GitHub، لأن الجلسة ما تقدر تحذف فروع.

## 7. النص والصوت والتجميع

```bash
NODE_PATH=$(npm root -g) node $SK/scripts/text_cards.js cards.json $P/text
~/.bpy-venv/bin/python $SK/scripts/sound.py sound.json $P/sound.wav
python3 $SK/scripts/assemble.py --frames $P/frames --fps 24 --cards cards.json --textdir $P/text --audio $P/sound.wav --out $P/final.mp4
bash $SK/scripts/contact.sh $P/check.png $P/final.mp4 1 3.5 6 9
```

- أمثلة جاهزة: [cards.json](assets/examples/transistor/cards.json) و[sound.json](assets/examples/transistor/sound.json). وقّت النص والصوت على أحداث المشهد نفسها (الثانية = رقم الإطار ÷ fps).
- النص: ٥ كلمات كحد أقصى للسطر، وتحت ثلث الشاشة (`bottom: 430`) عشان ما تغطيه أزرار الريلز. تأكد إن السكربت يطبع `(Cairo)` وما يطبع `FONT NOT LOADED`.
- **أنت ما تسمع.** تأكد من الصوت بالأرقام: `ffmpeg -i sound.wav -af ebur128=peak=true -f null -`، وبالطيف: `showspectrumpic`. وقل للمستخدم وين يركز وهو يسمع.
- **تحقق قبل التسليم:** اقرأ `check.png` وتأكد إن النصوص ظاهرة في كل لقطة.
- `assemble.py --upto N` يطلّع مسودة من الإطارات الجاهزة. أرسلها للمستخدم وأنت تنتظر الرندر.

## 8. التسليم

- `SendUserFile` بالفيديو مع `display: render`. على الآيباد يفتحه المستخدم من البطاقة، ثم مشاركة، ثم «حفظ الفيديو».
- ملفات الـ scratchpad تنمسح لما تنتهي الجلسة. سلّم الفيديو قبل، وإذا المستخدم يبي يعدّل بعدين، ارفع سكربتات المشروع (مو الإطارات) على فرعه.
- آخر رسالة: وش انعمل، والمواصفات، وأي شي باقي عليه هو (مثل حذف الفروع).

## مشاكل واجهناها

كلها في [references/pitfalls.md](references/pitfalls.md). اقرأها قبل أول رندر طويل.
