"""Write Auld Lang Syne in YuE2's native ABC dialect (L:1/16, full 16-unit bars, ties across barlines,
pickup as a rest inside a full bar, <=4-bar Vocal/Ins blocks).

usage: python make_abc.py [--chords] > file.abc
"""
import sys

A = [("C",1),("F",1.5),("E",.5),("F",1),("A",1),("G",1.5),("F",.5),("G",1)]
B = [("A",1),("F",1.5),("F",.5),("A",1),("c",1),("d",3)]
C = [("d",1),("c",1.5),("A",.5),("A",1),("F",1),("G",1.5),("F",.5),("G",1)]
D = [("A",1),("F",1.5),("D",.5),("D",1),("C",1),("F",3)]
E = [("d",1),("c",1.5),("A",.5),("A",1),("c",1),("d",3)]
SECTIONS = [("verse", A + B + C + D), ("chorus", C + E + C + D)]
CHORDS = ["F", "F", "C7", "F", "Bb", "F", "C7", "Bb", "F"]  # per bar, incl. the pickup bar
BAR, Q = 16, 4  # units per bar, units per quarter note
chords = "--chords" in sys.argv

def render(notes):
    events = [(None, BAR - Q)] + [(p, int(round(b * Q))) for p, b in notes]  # 3-beat rest, then the pickup
    pad = (-sum(u for _, u in events)) % BAR
    if pad: events.append((None, pad))
    bars, cur, fill = [], [], 0
    for p, u in events:
        first = True
        while u > 0:
            take = min(u, BAR - fill)
            cur.append([p, take, False])
            if not first: cur[-1][2] = True          # continuation of a split note
            fill += take; u -= take; first = False
            if fill == BAR: bars.append(cur); cur, fill = [], 0
    assert not cur
    out = []
    for i, bar in enumerate(bars):
        toks = []
        for j, (p, take, cont) in enumerate(bar):
            t = ("z" if p is None else p) + (str(take) if take > 1 else "")
            nxt = bars[i + 1][0] if j == len(bar) - 1 and i + 1 < len(bars) else None
            if p is not None and nxt and nxt[2]: t += "-"   # tie into the split continuation in the next bar
            toks.append(t)
        prefix = f'"{CHORDS[i % len(CHORDS)]}"' if chords else ""
        out.append(prefix + "".join(toks))
    return out

lines = ["X:1", "T:", "M:4/4", f"L:1/{BAR}", "Q:1/4=80",
         'V: Vocal clef=treble name="Vocal Melody" snm="Vocal"',
         'V: Ins clef=treble name="Ins Melody" snm="Inst."', "K:F"]
for name, notes in SECTIONS:
    bars = render(notes)
    lines.append(f"% {name}")
    for k in range(0, len(bars), 4):
        grp = bars[k:k + 4]
        lines += ["V: Vocal", "|".join(grp) + "|", "V: Ins", f"Z{len(grp)}|" if len(grp) > 1 else "Z|"]
print("\n".join(lines))
