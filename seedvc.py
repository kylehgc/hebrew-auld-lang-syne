"""Re-voice the dry vocal with Seed-VC (free Hugging Face Space, zero-shot singing voice conversion).

usage: python seedvc.py out/sung_dry.wav ref/ref_clip_28s.wav out/seedvc_out.wav [--steps 50]
Reference should be clean solo singing, <= ~28 s (the Space truncates longer clips).
"""
import os, shutil, sys
from gradio_client import Client, handle_file

args = sys.argv[1:]
src, ref, out = args[0], args[1], args[2]
steps = int(args[args.index("--steps") + 1]) if "--steps" in args else 50

c = Client(os.environ.get("SEEDVC_URL", "Plachta/Seed-VC"), token=os.environ.get("HF_TOKEN"))  # SEEDVC_URL for a private duplicate
_, full = c.predict(
    source_audio_path=handle_file(src), target_audio_path=handle_file(ref),
    diffusion_steps=steps, length_adjust=1.0, inference_cfg_rate=0.7,
    f0_condition=True, auto_f0_adjust=False, pitch_shift=0,  # keep our melody exactly
    api_name="/predict_1")
shutil.copy(full, out)
print("wrote", out)
