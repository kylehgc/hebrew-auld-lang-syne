"""Synthesize a piano-ish accompaniment from timeline.json and mix it under a vocal.

usage: python accomp.py vocal.wav out.mp3 [--intro 4] [--vocal_db 0] [--band_db -8]
Chords follow Auld Lang Syne (I, V7, IV) per bar, transposed to match the vocal.
"""
import json, subprocess, sys
import numpy as np, soundfile as sf

args = sys.argv[1:]
vocal_path, out = args[0], args[1]
opt = lambda k, d: float(args[args.index(k) + 1]) if k in args else d
intro_beats, vocal_db, band_db = opt("--intro", 4), opt("--vocal_db", 0), opt("--band_db", -8)

tl = json.load(open("timeline.json"))
notes, T = tl["notes"], tl["transpose"]
beat = 60 / tl["bpm"]
sr = 44100

# chords per bar, verse then chorus, relative to F major (semitone offsets from F): I, V7, IV
I, V7, IV = [0, 4, 7], [7, 11, 14, 17], [5, 9, 12]
BARS = [I, V7, I, IV, I, V7, IV, I] * 2  # 16 bars, 4 beats each, after a 1-beat pickup
F4 = 65  # midi F4; chord voicings sit around F3-F4 after transpose, bass an octave lower
hz = lambda m: 440 * 2 ** ((m - 69) / 12)

# bar k starts after the pickup note of the half-line that begins it; use actual vocal timing
# half-lines begin at notes 0, 8, 14, 22, 28, 36, 42, 50 (8,6,8,6 pattern); each = 1 pickup beat + 7 beats of 2 bars
starts = [0, 8, 14, 22, 28, 36, 42, 50]
bar_times = []
for i, s in enumerate(starts):
    pickup_end = notes[s]["start"] + notes[s]["dur"]
    half_end = notes[starts[i + 1]]["start"] if i + 1 < len(starts) else notes[-1]["start"] + notes[-1]["dur"]
    bar_len = (half_end - pickup_end) / 7 * 4  # bars are 4 beats; half-line holds 7 post-pickup beats
    bar_times += [(pickup_end, bar_len), (pickup_end + bar_len, bar_len)]

total = notes[-1]["start"] + notes[-1]["dur"] + 2.0
band = np.zeros(int((total + intro_beats * beat) * sr))
offset = intro_beats * beat

def tone(f, dur, vel=1.0, decay=1.8):
    t = np.arange(int(dur * sr)) / sr
    env = np.exp(-t * decay) * np.minimum(1, t / 0.008)
    w = np.sin(2*np.pi*f*t) + 0.5*np.sin(4*np.pi*f*t) * np.exp(-t*3) + 0.25*np.sin(6*np.pi*f*t) * np.exp(-t*5)
    return vel * env * w

def add(sig, at):
    i = int(at * sr); j = min(len(band), i + len(sig))
    if j > i: band[i:j] += sig[:j - i]

# intro: tonic chord, arpeggiated, one bar
for k, m in enumerate([F4 - 12, F4, F4 + 4, F4 + 7]):
    add(tone(hz(m + T), intro_beats * beat, 0.5), k * beat * 0.5)

for (t0, bl), chord in zip(bar_times, BARS):
    b = bl / 4
    bass = F4 - 12 + chord[0]
    add(tone(hz(bass + T), bl, 0.9, 1.2), offset + t0)                 # bass on 1
    add(tone(hz(bass + T + (7 if len(chord) == 3 else 5)), b * 2, 0.5, 1.5), offset + t0 + 2 * b)  # fifth on 3
    for bi in range(4):                                                  # chord tones, broken: 1 & 3 full, 2 & 4 light
        vel = 0.55 if bi % 2 == 0 else 0.3
        for m in chord[:3]:
            add(tone(hz(F4 + m + T), b * 1.6, vel), offset + t0 + bi * b + 0.01 * chord.index(m))

# final tonic ring-out
end = bar_times[-1][0] + bar_times[-1][1]
for m in [F4 - 12, F4, F4 + 4, F4 + 7, F4 + 12]:
    add(tone(hz(m + T), 3.0, 0.6, 0.9), offset + end)

band /= np.abs(band).max() + 1e-9
sf.write("out/band.wav", band * 0.8, sr)

v, vsr = sf.read(vocal_path)
if v.ndim > 1: v = v.mean(1)
subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", vocal_path, "-i", "out/band.wav",
    "-filter_complex",
    f"[0:a]adelay={int(offset*1000)}|{int(offset*1000)},volume={vocal_db}dB,aecho=0.9:0.3:60:0.12[v];"
    f"[1:a]volume={band_db}dB,aecho=0.8:0.4:90:0.2,lowpass=f=6000[b];"
    "[v][b]amix=inputs=2:duration=longest:normalize=0,loudnorm=I=-14:TP=-1.5", "-b:a", "192k", out], check=True)
print(f"wrote {out}, intro {intro_beats:g} beats, {len(bar_times)} bars")
