# Hebrew Auld Lang Syne

Auld Lang Syne sung in Hebrew in a cloned voice, with a sampled orchestral-pop arrangement. Zero cost end to end.

Final tracks: `out/auld_lang_syne_he_arranged.mp3` (Mandy Patinkin clone), `out/jack_arranged.mp3` (Jack Black clone)

## Pipeline

1. **Reference clip** — `ref/ref_clip_28s.wav`, 28 s of a cappella singing pulled from YouTube with yt-dlp + ffmpeg.
2. **Voice clone TTS** — `sing.py` sends each lyric line to Fish Audio S2.1 Pro (free) via OpenRouter with the clip as `input_references`. Lines cache in `lines/<tag>/`.
3. **Melody** — `sing.py` splits each line into syllables by energy peaks, maps one syllable per melody note, stretches vowels, and rewrites pitch with the WORLD vocoder. Adds scoops, detune, drift, vibrato, dynamics. Writes `out/<tag>_sung_dry.wav` and `out/<tag>_timeline.json` (exact note timings).
4. **Re-voice** — `seedvc.py` runs the dry vocal through Seed-VC (zero-shot singing voice conversion, free HF Space) with the reference clip. Removes vocoder buzz, restores timbre.
5. **Arrangement** — `arrange.py` renders piano / strings / cello / bass / harp (verse) + flute / choir / glockenspiel (chorus) from the timeline through a GM SoundFont, mixes under the vocal.

```bash
set OPENROUTER_API_KEY=sk-or-...
python sing.py ref/ref_clip.wav --tag mandy                       # -> out/mandy_sung_dry.wav, out/mandy_timeline.json
python seedvc.py out/mandy_sung_dry.wav ref/ref_clip_28s.wav out/seedvc_out_28s.wav
python arrange.py out/seedvc_out_28s.wav out/auld_lang_syne_he_arranged.mp3 --tag mandy

# another singer: new reference clip, new tag
python sing.py ref/jack_clip.wav --tag jack --transpose -12
python seedvc.py out/jack_sung_dry.wav ref/jack_clip.wav out/jack_seedvc.wav
python arrange.py out/jack_seedvc.wav out/jack_arranged.mp3 --tag jack
```

## Setup

```bash
pip install numpy soundfile pyworld "setuptools<81" gradio_client
pip install --no-deps tinysoundfont
curl -L -o sf/GeneralUser.sf2 https://github.com/mrbumpy409/GeneralUser-GS/raw/main/GeneralUser-GS.sf2
```

Needs ffmpeg on PATH. Python 3.14 on Windows works.

## Knobs

- `sing.py --tag NAME --bpm 80 --transpose -10 --seed 7` — transpose is auto-picked from the speaker's median pitch if omitted; check it, a deep voice can auto-pick too low (Jack came out -17, -12 sounds better).
- `arrange.py --band_db -6 --vocal_db 0 --intro 4` — instrument levels and panning are the `VOLUME` / `PAN` dicts at the top.
- Lyrics live in `LINES` in `sing.py`; syllable counts must stay 8,6,8,6,8,6,8,6 to match the melody.

## Other scripts

- `auld_lang_syne_he.py` — original one-shot TTS call (whole lyric, no melody).
- `autotune.py` — scale-snap auto-tune. Fixes pitch, can't add a melody.
- `melodize.py` — forces the melody onto an existing vocal by phrase. Superseded by `sing.py`.
- `accomp.py` — earlier sine-synth piano accompaniment. Superseded by `arrange.py`.
