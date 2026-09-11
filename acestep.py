"""Generate a sung Hebrew Auld Lang Syne with ACE-Step 1.5 (free HF Space).

usage: ACE_URL=https://you-ace-step-v1-5.hf.space HF_TOKEN=hf_...        python acestep.py out/ace_cover.mp3 --cover out/auld_lang_syne_he_arranged.mp3 [--strength 0.7] [--caption "..."]
Cover mode re-sings the source track's melody and structure with LYRICS and the caption.
Without --cover it composes its own melody (text2music). ACE_URL defaults to the public ZeroGPU Space,
where cover mode is currently broken; run your own copy on a GPU (see README).
"""
import shutil, sys
from gradio_client import Client, handle_file

args = sys.argv[1:]
out = args[0]
cover = args[args.index("--cover") + 1] if "--cover" in args else None
strength = float(args[args.index("--strength") + 1]) if "--strength" in args else 0.7
caption = args[args.index("--caption") + 1] if "--caption" in args else (
    "slow tender ballad, solo male baritone vocal, a cappella, no instruments, warm intimate, "
    "traditional folk melody, New Year's Eve song, clear Hebrew diction, 80 bpm")

LYRICS = """[verse]
הַאִם נִשְׁכַּח רֵעִים מִכְּבָר
וְלֹא נִזְכֹּר אוֹתָם
הַאִם נִשְׁכַּח רֵעִים מִכְּבָר
וְיָמִים שֶׁחָלְפוּ

[chorus]
לְזֵכֶר יָמִים שֶׁהָיוּ
לְזֵכֶר הַיָּמִים
נָרִים כּוֹסִית שֶׁל אַהֲבָה
לְזֵכֶר הַיָּמִים
"""

import os
c = Client(os.environ.get("ACE_URL", "ACE-Step/Ace-Step-v1.5"), token=os.environ.get("HF_TOKEN"))  # ACE_URL=http://host:7860 for a local server
model = args[args.index("--model") + 1] if "--model" in args else "acestep-v15-xl-turbo"  # needs SERVICE_MODE_DIT_MODEL_2 blanked on a 24 GB card, see README
res = c.predict(
    model, "custom", "", "he",
    caption, LYRICS, 80, "G major", "4/4", "he",
    8, 7.0, True, "-1",
    None,                       # reference_audio
    55 if cover is None else -1,  # duration (-1 = follow source in cover mode)
    1,                          # batch size
    handle_file(cover) if cover else None,  # src_audio
    "", 0.0, -1, "Fill the audio semantic mask based on the given conditions:",
    strength, "cover" if cover else "text2music",
    False, 0.0, 1.0, 3.0, "ode", "", "mp3",
    0.85, True, 2.0, 0, 0.9, "NO USER INPUT", True, True, True,
    False, True, False, False, 0.5, 8, "vocals", [], False,
    api_name="/generation_wrapper")
status, details, files = res[10], res[9], res[8]
print("status:", status)
if not (isinstance(files, list) and files):  # audio players come back as gr.update(); the download list holds the mp3s
    sys.exit(f"no audio returned: {status}")
audio = files[0]
print(str(details)[:300])
shutil.copy(audio, out)
print("wrote", out)
