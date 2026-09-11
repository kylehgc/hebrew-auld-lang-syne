"""Force the Auld Lang Syne melody onto a spoken/sung vocal.

usage: python melodize.py in.wav out.wav [--bpm 84] [--key F]
Splits the vocal into phrases at pauses, stretches each to its melody line, replaces pitch with the notes.
"""
import sys, warnings
import numpy as np, soundfile as sf
warnings.filterwarnings("ignore")
import pyworld as pw

NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
def n(name): return NAMES.index(name[:-1]) + 12 * (int(name[-1]) + 1)

# (note, beats) in F major; 8 half-lines matching the 8 lyric lines in auld_lang_syne_he.py
A = [("C4",1),("F4",1.5),("E4",.5),("F4",1),("A4",1),("G4",1.5),("F4",.5),("G4",1)]
B = [("A4",1),("F4",1.5),("F4",.5),("A4",1),("C5",1),("D5",3)]
C = [("D5",1),("C5",1.5),("A4",.5),("A4",1),("F4",1),("G4",1.5),("F4",.5),("G4",1)]
D = [("A4",1),("F4",1.5),("D4",.5),("D4",1),("C4",1),("F4",3)]
E = [("D5",1),("C5",1.5),("A4",.5),("A4",1),("C5",1),("D5",3)]
MELODY = [A, B, C, D, C, E, C, D]

args = sys.argv[1:]
bpm = float(args[args.index("--bpm") + 1]) if "--bpm" in args else 84
key = args[args.index("--key") + 1] if "--key" in args else "F"
transpose = NAMES.index(key) - NAMES.index("F")
inp, out = args[0], args[1]

x, sr = sf.read(inp, dtype="float64")
if x.ndim > 1: x = x.mean(1)
hop = 5.0  # ms
f0, t = pw.harvest(x, sr, f0_floor=70, f0_ceil=800, frame_period=hop)
f0 = pw.stonemask(x, f0, t, sr)
sp = pw.cheaptrick(x, f0, t, sr)
ap = pw.d4c(x, f0, t, sr)

# phrases = voiced runs separated by unvoiced gaps > gap_ms
gap_ms = 150
voiced = f0 > 0
runs, start = [], None
for i, v in enumerate(np.append(voiced, False)):
    if v and start is None: start = i
    if not v and start is not None: runs.append([start, i]); start = None
phrases = [runs[0]]
for s, e in runs[1:]:
    if (s - phrases[-1][1]) * hop <= gap_ms: phrases[-1][1] = e
    else: phrases.append([s, e])
print(f"found {len(phrases)} phrases, need {len(MELODY)}")
if len(phrases) != len(MELODY):  # ponytail: merge/split naively; retune gap_ms if this fires
    while len(phrases) > len(MELODY):
        gaps = [phrases[i+1][0] - phrases[i][1] for i in range(len(phrases)-1)]
        i = int(np.argmin(gaps)); phrases[i][1] = phrases[i+1][1]; del phrases[i+1]
    while len(phrases) < len(MELODY):
        i = int(np.argmax([e - s for s, e in phrases])); s, e = phrases[i]; m = (s + e) // 2
        phrases[i:i+1] = [[s, m], [m, e]]

beat = 60 / bpm
new_f0, new_sp, new_ap = [], [], []
for (s, e), line in zip(phrases, MELODY):
    src_frames = np.arange(s, e)
    total_beats = sum(b for _, b in line)
    for note, beats in line:
        nf = int(round(beats * beat * 1000 / hop))
        new_f0.append(np.full(nf, 440 * 2 ** ((n(note) + transpose - 69) / 12)))
        new_sp.append(np.zeros((nf, sp.shape[1]))); new_ap.append(np.zeros((nf, ap.shape[1])))
    # fill spectral envelopes by stretching the whole phrase over the whole line
    line_frames = sum(len(a) for a in new_f0[-len(line):])
    idx = np.linspace(s, e - 1, line_frames).astype(int)
    stretched_sp, stretched_ap = sp[idx], ap[idx]
    k = 0
    for j in range(len(line)):
        nf = len(new_f0[-len(line) + j])
        new_sp[-len(line) + j] = stretched_sp[k:k+nf]; new_ap[-len(line) + j] = stretched_ap[k:k+nf]; k += nf

f0o = np.concatenate(new_f0); spo = np.vstack(new_sp); apo = np.vstack(new_ap)
y = pw.synthesize(f0o, np.ascontiguousarray(spo), np.ascontiguousarray(apo), sr, frame_period=hop)
sf.write(out, np.clip(y, -1, 1), sr)
print(f"key {key}, {bpm} bpm, {len(y)/sr:.1f}s, wrote {out}")
