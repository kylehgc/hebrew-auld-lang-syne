"""Minimal Gradio wrapper around YuE2 for a private Hugging Face Space.

Inputs: style, lyrics, optional ABC score, cot mode, seed. Output: audio.flac + the score YuE2 used.
"""
import os, tempfile
import gradio as gr
from yue2 import YuE2Pipeline
from yue2.protocol import Sampling

pipe = YuE2Pipeline.from_pretrained("m-a-p/YuE2-3B", vae="m-a-p/YuE2-Vae", device="cuda")
pipe.__enter__()


def generate(style, lyrics, abc, cot, seed, temperature, cfg_scale):
    req = dict(style=style, lyrics=lyrics, cot=cot, seed=int(seed))
    if abc and abc.strip():
        req["abc"] = abc
    if cfg_scale and float(cfg_scale) > 0:
        req["cfg_scale"] = float(cfg_scale)
    sem = Sampling(temperature=float(temperature))  # other fields stay at YuE2 defaults
    song = pipe(**req, semantic_sampling=sem)
    out = tempfile.mkdtemp()
    song.save_artifacts(out)
    score = song.abc or ""
    return os.path.join(out, "audio.flac"), score, str(song.truncated)


demo = gr.Interface(
    fn=generate,
    inputs=[
        gr.Textbox(label="style", value="Hebrew, slow tender ballad, warm male baritone lead vocal, piano and strings, 80 BPM"),
        gr.Textbox(label="lyrics", lines=12),
        gr.Textbox(label="abc score (optional)", lines=12),
        gr.Dropdown(["full", "melody", "off"], value="melody", label="cot"),
        gr.Number(value=831001, label="seed", precision=0),
        gr.Number(value=1.0, label="semantic temperature (lower = more literal)"),
        gr.Number(value=0, label="cfg_scale (0 = model default)"),
    ],
    outputs=[gr.Audio(label="song", type="filepath"), gr.Textbox(label="score used"), gr.Textbox(label="truncated")],
    title="YuE2",
)
demo.queue().launch()
