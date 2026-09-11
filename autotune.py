"""Snap a vocal's pitch to the nearest note of its best-fitting major scale (classic auto-tune).

usage: python autotune.py in.wav out.wav [--strength 1.0] [--key F]
Convert mp3 first: ffmpeg -i in.mp3 -ac 1 -ar 44100 in.wav
"""
import sys, warnings
import numpy as np, soundfile as sf
warnings.filterwarnings("ignore")
import pyworld as pw

MAJOR = np.array([0, 2, 4, 5, 7, 9, 11])
NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

args = sys.argv[1:]
strength = float(args[args.index("--strength") + 1]) if "--strength" in args else 1.0
key = args[args.index("--key") + 1] if "--key" in args else None
inp, out = args[0], args[1]

x, sr = sf.read(inp, dtype="float64")
if x.ndim > 1: x = x.mean(1)
f0, t = pw.harvest(x, sr, f0_floor=70, f0_ceil=800)
f0 = pw.stonemask(x, f0, t, sr)
sp = pw.cheaptrick(x, f0, t, sr)
ap = pw.d4c(x, f0, t, sr)

voiced = f0 > 0
midi = np.zeros_like(f0)
midi[voiced] = 69 + 12 * np.log2(f0[voiced] / 440)

if key is None:  # pick the major key whose scale covers the most sung pitch
    hist = np.bincount(np.round(midi[voiced]).astype(int) % 12, minlength=12)
    key = NAMES[int(np.argmax([hist[(MAJOR + k) % 12].sum() for k in range(12)]))]
scale = (MAJOR + NAMES.index(key)) % 12

def snap(m):
    cands = np.array([12 * o + s for o in range(0, 11) for s in scale])
    return cands[np.abs(cands - m).argmin()]

target = np.array([snap(m) if v else 0 for m, v in zip(midi, voiced)], dtype=float)
new_midi = midi + strength * (target - midi)
new_f0 = np.where(voiced, 440 * 2 ** ((new_midi - 69) / 12), 0.0)

y = pw.synthesize(new_f0, sp, ap, sr)
sf.write(out, np.clip(y, -1, 1), sr)
print(f"key {key} major, strength {strength}, wrote {out}")
