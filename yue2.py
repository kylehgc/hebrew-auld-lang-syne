"""Generate a sung Hebrew Auld Lang Syne with YuE2 via the private Space in yue2_space/.

usage: YUE2_URL=https://<you>-yue2.hf.space HF_TOKEN=hf_... python yue2.py out/yue2_take.flac [--seed 831001] [--cot melody] [--style "..."]
Uses auld_lang_syne.abc as the melody and lyrics_he.txt as the words, so it sings the real tune.
"""
import os, shutil, sys
from gradio_client import Client

args = sys.argv[1:]
out = args[0]
opt = lambda k, d: args[args.index(k) + 1] if k in args else d
seed = int(opt("--seed", 831001))
cot = opt("--cot", "melody")
style = opt("--style", "Hebrew, slow tender ballad, warm male baritone lead vocal, piano and strings, intimate, unhurried phrasing, 80 BPM")
abc = open("auld_lang_syne.abc", encoding="utf-8").read() if cot != "off" else ""
lyrics = open("lyrics_he.txt", encoding="utf-8").read()

c = Client(os.environ["YUE2_URL"], token=os.environ.get("HF_TOKEN"))
audio, score, truncated = c.predict(style, lyrics, abc, cot, seed, api_name="/predict")
print("truncated:", truncated)
shutil.copy(audio, out)
open(out + ".abc", "w", encoding="utf-8").write(score)
print("wrote", out)
