"""Sing Auld Lang Syne in Hebrew: per-line TTS voice clone -> one syllable per melody note -> vibrato -> mp3.

usage: OPENROUTER_API_KEY=... python sing.py ref/ref_clip.wav [--tag mandy] [--bpm 80] [--transpose -10]
Cached line wavs live in lines/; delete one to regenerate it.
"""
import base64, json, os, subprocess, sys, urllib.request, warnings
import numpy as np, soundfile as sf
warnings.filterwarnings("ignore")
import pyworld as pw

NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
def n(name): return NAMES.index(name[:-1]) + 12 * (int(name[-1]) + 1)

A = [("C4",1),("F4",1.5),("E4",.5),("F4",1),("A4",1),("G4",1.5),("F4",.5),("G4",1)]
B = [("A4",1),("F4",1.5),("F4",.5),("A4",1),("C5",1),("D5",3)]
C = [("D5",1),("C5",1.5),("A4",.5),("A4",1),("F4",1),("G4",1.5),("F4",.5),("G4",1)]
D = [("A4",1),("F4",1.5),("D4",.5),("D4",1),("C4",1),("F4",3)]
E = [("D5",1),("C5",1.5),("A4",.5),("A4",1),("C5",1),("D5",3)]
MELODY = [A, B, C, D, C, E, C, D]

# syllable counts 8,6,8,6,8,6,8,6 to match note counts
LINES = [
    "הַאִם נִשְׁכַּח רֵעִים מִכְּבָר",      # ha-im nish-kakh re-im mi-kvar
    "וְלֹא נִזְכֹּר אוֹתָם",               # ve-lo niz-kor o-tam
    "הַאִם נִשְׁכַּח רֵעִים מִכְּבָר",
    "וְיָמִים שֶׁחָלְפוּ",                 # ve-ya-mim she-khal-fu
    "לְזֵכֶר יָמִים שֶׁהָיוּ",             # le-ze-kher ya-mim she-ha-yu
    "לְזֵכֶר הַיָּמִים",                   # le-ze-kher ha-ya-mim
    "נָרִים כּוֹסִית שֶׁל אַהֲבָה",         # na-rim ko-sit shel a-ha-va
    "לְזֵכֶר הַיָּמִים",
]

args = sys.argv[1:]
ref = args[0]
bpm = float(args[args.index("--bpm") + 1]) if "--bpm" in args else 80
transpose = int(args[args.index("--transpose") + 1]) if "--transpose" in args else None  # semitones from F; auto if omitted
tag = args[args.index("--tag") + 1] if "--tag" in args else "mandy"  # keeps separate singers' files apart
HOP = 5.0
os.makedirs(f"lines/{tag}", exist_ok=True); os.makedirs("out", exist_ok=True)

def tts(text, path):
    mime = "audio/mpeg" if ref.lower().endswith(".mp3") else "audio/wav"
    with open(ref, "rb") as f: data = f"data:{mime};base64,{base64.b64encode(f.read()).decode()}"
    body = {"model": "fish-audio/s2.1-pro-free:free", "input": text, "response_format": "mp3",
            "input_references": [{"type": "input_audio", "input_audio": {"data": data}}]}
    req = urllib.request.Request("https://openrouter.ai/api/v1/audio/speech", data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r, open(path + ".mp3", "wb") as f: f.write(r.read())
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", path + ".mp3", "-ac", "1", "-ar", "44100", path], check=True)

def syllables(x, sr, f0, count):
    """Frame index ranges for `count` syllables: energy peaks in voiced regions, else even split."""
    frame = int(sr * HOP / 1000)
    rms = np.array([np.sqrt(np.mean(x[i*frame:(i+1)*frame]**2)) for i in range(len(f0))])
    k = 7; rms = np.convolve(rms, np.ones(k)/k, "same")
    voiced = f0 > 0
    first, last = np.argmax(voiced), len(voiced) - np.argmax(voiced[::-1])
    peaks = [i for i in range(first+1, last-1) if voiced[i] and rms[i] >= rms[i-1] and rms[i] > rms[i+1]]
    # greedy: keep strongest peaks, spaced at least 45% of the average syllable length apart
    min_gap = max(80, 0.45 * (last - first) * HOP / count)
    peaks.sort(key=lambda i: -rms[i]); kept = []
    for p in peaks:
        if all(abs(p - q) * HOP >= min_gap for q in kept): kept.append(p)
    kept = sorted(kept)
    if len(kept) < count:  # ponytail: even split fallback; tune min-distance if this fires often
        print("   even split"); bounds = np.linspace(first, last, count + 1).astype(int)
    else:
        kept = sorted(sorted(kept, key=lambda i: -rms[i])[:count])
        bounds = [first] + [int(kept[i] + np.argmin(rms[kept[i]:kept[i+1]])) for i in range(count-1)] + [last]
    return [(bounds[i], bounds[i+1]) for i in range(count)]

beat = 60 / bpm
analysed = []
for li, (text, line) in enumerate(zip(LINES, MELODY)):
    path = f"lines/{tag}/{li}.wav"
    if not os.path.exists(path): print(f"tts line {li}"); tts(text, path)
    x, sr = sf.read(path, dtype="float64")
    if x.ndim > 1: x = x.mean(1)
    f0, t = pw.harvest(x, sr, f0_floor=70, f0_ceil=800, frame_period=HOP)
    f0 = pw.stonemask(x, f0, t, sr); sp = pw.cheaptrick(x, f0, t, sr); ap = pw.d4c(x, f0, t, sr)
    analysed.append((x, sr, f0, sp, ap))
if transpose is None:  # put the melody's median note 2 semitones above his median speaking pitch
    spk = np.median(np.concatenate([f0[f0 > 0] for _, _, f0, _, _ in analysed]))
    mel = np.median([n(note) for line in MELODY for note, _ in line])
    transpose = int(round(69 + 12 * np.log2(spk / 440) + 2 - mel))
print(f"transpose {transpose:+d} semitones")

def stretch_idx(s, e, nf):
    """Source frame indices for nf output frames, plus a mask of the held vowel.
    Onset and release play at natural speed; only the vowel core (35%..85%) is stretched, smoothly."""
    L = e - s
    if nf <= L: return np.linspace(s, e - 1, nf).astype(int), np.zeros(nf, bool)
    core0, core1 = s + int(L * 0.35), s + int(L * 0.85)
    head = np.arange(s, core0); tail = np.arange(core1, e)
    need = nf - len(head) - len(tail)
    mid = np.linspace(core0, max(core1 - 1, core0), need).astype(int)
    held = np.concatenate([np.zeros(len(head), bool), np.ones(need, bool), np.zeros(len(tail), bool)])
    return np.concatenate([head, mid, tail])[:nf], held[:nf]

rng = np.random.default_rng(int(args[args.index("--seed") + 1]) if "--seed" in args else 7)
cents = lambda c: 2 ** (c / 1200)
F0, SP, AP = [], [], []
timeline, cursor = [], 0.0
for li, ((x, sr, f0, sp, ap), line) in enumerate(zip(analysed, MELODY)):
    segs = syllables(x, sr, f0, len(line))
    print(f"line {li}: {len(line)} notes, syllable frames {[e-s for s,e in segs]}")
    durs = np.array([b for _, b in line]) * beat * (1 + rng.normal(0, 0.03, len(line)))  # loose timing
    durs *= sum(b for _, b in line) * beat / durs.sum()
    prev = None
    for k, ((s, e), (note, _)) in enumerate(zip(segs, line)):
        nf = int(round(durs[k] * 1000 / HOP))
        idx, held = stretch_idx(s, e, nf)
        target = 440 * 2 ** ((n(note) + transpose - 69) / 12) * cents(rng.normal(0, 8))  # per-note detune
        tt = np.arange(nf) * HOP / 1000
        dur = nf * HOP / 1000
        # scoop in from below (or glide from previous note), then settle
        start = prev if prev is not None else target * cents(-80)
        if prev is not None and abs(np.log2(target / prev)) < 0.01: start = target * cents(-40)
        hz = start + (target - start) * (1 - np.exp(-tt / 0.06))
        # vibrato only on notes long enough to hold; rate and depth vary per note
        if dur > 0.45:
            rate, depth = rng.uniform(5.0, 6.3), rng.uniform(20, 40)
            fade = np.clip((tt - 0.12) / (dur * 0.45), 0, 1)
            hz = hz * cents(depth * np.sin(2 * np.pi * rate * tt + rng.uniform(0, 6.28)) * fade)
        # slow drift
        hz = hz * cents(np.cumsum(rng.normal(0, 0.6, nf)))
        if k == len(line) - 1:  # phrase ending falls off slightly
            hz = hz * cents(-40 * np.clip((tt - dur + 0.15) / 0.15, 0, 1))
        # dynamics: soft attack, swell on long notes, phrase-final decay
        env = np.minimum(1, tt / 0.03)
        if dur > 0.6: env = env * (0.8 + 0.2 * np.sin(np.pi * np.clip(tt / dur, 0, 1)))
        if k == len(line) - 1: env = env * np.clip(1 - (tt - dur + 0.3) / 0.6, 0.5, 1)
        breath = np.where(held, 0.08, 0.0)[:, None]  # a little air on held vowels
        timeline.append({"line": li, "note": n(note) + transpose, "start": cursor, "dur": dur}); cursor += dur
        F0.append(np.where((f0[idx] > 0) | held, hz, 0.0))
        SP.append(sp[idx] * (env ** 2)[:, None]); AP.append(ap[idx] + (1 - ap[idx]) * breath); prev = target
    tail = slice(segs[-1][1], min(len(f0), segs[-1][1] + int(120 / HOP)))
    F0.append(np.zeros(tail.stop - tail.start)); SP.append(sp[tail]); AP.append(ap[tail])
    cursor += (tail.stop - tail.start) * HOP / 1000
json.dump({"bpm": bpm, "transpose": transpose, "notes": timeline}, open(f"out/{tag}_timeline.json", "w"), indent=1)

y = pw.synthesize(np.concatenate(F0), np.ascontiguousarray(np.vstack(SP)), np.ascontiguousarray(np.vstack(AP)), sr, frame_period=HOP)
sf.write(f"out/{tag}_sung_dry.wav", np.clip(y, -1, 1), sr)
subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", f"out/{tag}_sung_dry.wav",
    "-af", "aecho=0.9:0.3:60:0.12,loudnorm", f"out/{tag}_sung.mp3"], check=True)
print(f"{len(y)/sr:.1f}s -> out/{tag}_sung.mp3")
