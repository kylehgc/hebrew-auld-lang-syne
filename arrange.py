"""Render a sampled orchestral-pop arrangement from timeline.json and mix it under a vocal.

usage: python arrange.py vocal.wav out.mp3 [--tag mandy] [--intro 4] [--vocal_db 0] [--band_db -6]
Verse: piano, strings, cello/bass, harp. Chorus adds flute on the melody, choir pad, glockenspiel.
"""
import json, subprocess, sys
import numpy as np, soundfile as sf, tinysoundfont as tsf

args = sys.argv[1:]
vocal_path, out = args[0], args[1]
opt = lambda k, d: float(args[args.index(k) + 1]) if k in args else d
intro_beats, vocal_db, band_db = opt("--intro", 4), opt("--vocal_db", 0), opt("--band_db", -6)

tag = args[args.index("--tag") + 1] if "--tag" in args else "mandy"
tl = json.load(open(f"out/{tag}_timeline.json"))
notes, T, beat, sr = tl["notes"], tl["transpose"], 60 / tl["bpm"], 44100
I, V7, IV = [0, 4, 7], [7, 11, 14, 17], [5, 9, 12]
BARS = [I, V7, I, IV, I, V7, IV, I] * 2
F4 = 65
starts = [0, 8, 14, 22, 28, 36, 42, 50]
bar_times = []
for i, s in enumerate(starts):
    pickup_end = notes[s]["start"] + notes[s]["dur"]
    half_end = notes[starts[i + 1]]["start"] if i + 1 < len(starts) else notes[-1]["start"] + notes[-1]["dur"]
    bl = (half_end - pickup_end) / 7 * 4
    bar_times += [(pickup_end, bl), (pickup_end + bl, bl)]
offset = intro_beats * beat
end = bar_times[-1][0] + bar_times[-1][1]
total = offset + end + 5.0

PIANO, STRINGS, CELLO, FLUTE, GLOCK, HARP, CHOIR, BASS = range(8)
PROGRAMS = {PIANO: 0, STRINGS: 48, CELLO: 42, FLUTE: 73, GLOCK: 9, HARP: 46, CHOIR: 52, BASS: 32}
VOLUME = {PIANO: 95, STRINGS: 80, CELLO: 90, FLUTE: 85, GLOCK: 70, HARP: 75, CHOIR: 70, BASS: 100}
PAN = {PIANO: 54, STRINGS: 64, CELLO: 74, FLUTE: 40, GLOCK: 90, HARP: 30, CHOIR: 64, BASS: 64}

events = []  # (time, chan, key, vel) ; vel 0 = off
def play(ch, key, t0, dur, vel):
    events.append((t0, ch, key, vel)); events.append((t0 + dur, ch, key, 0))

# --- intro: harp arpeggio + string swell on tonic
for k, m in enumerate([F4 - 12, F4, F4 + 4, F4 + 7, F4 + 12, F4 + 16, F4 + 19, F4 + 24]):
    play(HARP, m + T, k * beat * 0.5, intro_beats * beat, 70)
for m in [F4 - 12, F4, F4 + 4, F4 + 7]:
    play(STRINGS, m + T, 0, intro_beats * beat + 0.2, 45)

for bi, ((t0, bl), chord) in enumerate(zip(bar_times, BARS)):
    t0 += offset; b = bl / 4
    chorus = bi >= 8
    last = bi == len(bar_times) - 1
    root = F4 - 12 + chord[0]
    fifth = root + (7 if len(chord) == 3 else 5)
    tones = [F4 + m for m in chord[:3]]
    # bass + cello: root on 1, fifth on 3
    play(BASS, root - 12 + T, t0, b * 1.9, 100); play(BASS, fifth - 12 + T, t0 + 2 * b, b * 1.9, 85)
    play(CELLO, root + T, t0, bl + 0.1, 75 if chorus else 60)
    # strings: sustained chord, fuller in chorus
    for m in tones + ([tones[0] + 12] if chorus else []):
        play(STRINGS, m + T, t0 + 0.02, bl + 0.15, 78 if chorus else 55)
    if chorus:
        for m in tones: play(CHOIR, m + T, t0 + 0.05, bl + 0.1, 60)
    # piano: bass note on 1, broken chord on beats, extra colour in chorus
    play(PIANO, root + T, t0, b * 2, 85)
    for k in range(4):
        vel = (80 if k % 2 == 0 else 55) + (8 if chorus else 0)
        for j, m in enumerate(tones):
            play(PIANO, m + T, t0 + k * b + 0.012 * j, b * 1.4, vel)
        if chorus and k % 2 == 1: play(PIANO, tones[0] + 12 + T, t0 + k * b + b / 2, b * 0.8, 60)
    # harp arpeggio in verse, eighths
    if not chorus:
        arp = [tones[0], tones[1], tones[2], tones[0] + 12, tones[2], tones[1], tones[0], tones[1]]
        for k, m in enumerate(arp): play(HARP, m + T, t0 + k * b / 2, b, 62)

# chorus melody doubling: flute an octave up, glockenspiel on the first note of each bar
chorus_notes = [nt for nt in notes if nt["line"] >= 4]
for nt in chorus_notes:
    t0 = offset + nt["start"]
    play(FLUTE, nt["note"] + 12, t0 + 0.03, nt["dur"] - 0.06, 72)
bar_starts = [offset + t for t, _ in bar_times[8:]]
for nt in chorus_notes:
    t0 = offset + nt["start"]
    if any(abs(t0 - bs) < 0.12 for bs in bar_starts) or nt["dur"] > 1.5:
        play(GLOCK, nt["note"] + 12, t0, 1.5, 80)

# ending: everything holds the tonic, glock sparkle
tE = offset + end
for m in [F4 - 24, F4 - 12, F4, F4 + 4, F4 + 7, F4 + 12]:
    play(STRINGS, m + T, tE, 4.0, 80); play(CHOIR, m + T, tE, 4.0, 60)
    play(PIANO, m + T, tE, 4.0, 90)
play(BASS, F4 - 24 + T, tE, 4.0, 100); play(CELLO, F4 - 12 + T, tE, 4.0, 80)
for k, m in enumerate([F4 + 12, F4 + 16, F4 + 19, F4 + 24]):
    play(GLOCK, m + T, tE + k * 0.18, 3.0, 75)

# --- render
synth = tsf.Synth(gain=-6, samplerate=sr)
sfid = synth.sfload("sf/GeneralUser.sf2")
for ch, prog in PROGRAMS.items():
    synth.program_select(ch, sfid, 0, prog)
    synth.control_change(ch, 7, VOLUME[ch]); synth.control_change(ch, 10, PAN[ch]); synth.control_change(ch, 91, 40)
events.sort(key=lambda e: (e[0], e[3] != 0))  # note-offs before note-ons at the same instant
out_buf = np.zeros((int(total * sr), 2), dtype=np.float32)
pos = 0
for t, ch, key, vel in events:
    target = min(int(t * sr), len(out_buf))
    if target > pos:
        buf = synth.generate_simple(target - pos)
        out_buf[pos:target] = np.frombuffer(buf, dtype=np.float32).reshape(-1, 2); pos = target
    synth.noteon(ch, key, vel) if vel else synth.noteoff(ch, key)
if pos < len(out_buf):
    out_buf[pos:] = np.frombuffer(synth.generate_simple(len(out_buf) - pos), dtype=np.float32).reshape(-1, 2)
out_buf /= max(np.abs(out_buf).max(), 1e-9)
sf.write(f"out/{tag}_band.wav", out_buf * 0.9, sr)

ms = int(offset * 1000)
subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", vocal_path, "-i", f"out/{tag}_band.wav",
    "-filter_complex",
    f"[0:a]adelay={ms}|{ms},volume={vocal_db}dB,aecho=0.9:0.3:60:0.12,pan=stereo|c0=c0|c1=c0[v];"
    f"[1:a]volume={band_db}dB,aecho=0.8:0.5:110:0.22[b];"
    "[v][b]amix=inputs=2:duration=longest:normalize=0,loudnorm=I=-14:TP=-1.5", "-b:a", "192k", out], check=True)
print(f"wrote {out}: {len(events)//2} notes, {len(bar_times)} bars, {total:.1f}s")
