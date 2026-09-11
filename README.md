# Hebrew Auld Lang Syne

Auld Lang Syne sung in Hebrew in a cloned voice, with an orchestral-pop backing. Built from free and open models plus about two dollars of rented GPU.

Rendered audio is not in the repo; run the pipeline below to produce `out/ace_mandy_arranged.mp3` and `out/ace_jack_arranged.mp3`.

## How it works

```
lyrics ─► sing.py ─► arrange.py ─► acestep.py (cover) ─► seedvc.py ─► ffmpeg mix
          TTS clone   sampled band   real sung take       target voice   final mp3
          + melody
```

1. **`sing.py`** — clones a reference singer per lyric line with Fish Audio S2.1 Pro (free on OpenRouter), splits each line into syllables, maps one syllable per melody note with the WORLD vocoder, and humanizes the pitch. Output is on-melody but sounds like a vocoder. Also writes `out/<tag>_timeline.json`, the exact time of every note.
2. **`arrange.py`** — reads that timeline and renders piano, strings, cello, bass and harp for the verse, adding flute, choir and glockenspiel for the chorus, through a General MIDI SoundFont. Mixes it under a vocal.
3. **`acestep.py`** — runs ACE-Step 1.5 in *cover* mode on the arranged track. ACE-Step re-sings the melody and structure with the Hebrew lyrics as a real performance: breath, phrasing, timing. Asked for a cappella so the output is a clean vocal. This is the step that removes the autotune character.
4. **`seedvc.py`** — Seed-VC zero-shot singing voice conversion. Takes the ACE-Step vocal and a 15–28 s reference clip and returns the same performance in the reference singer's voice. No training.
5. **ffmpeg** mixes the converted vocal over the `arrange.py` band.

Steps 1–2 exist to give ACE-Step a melodically correct source to cover. Any well-sung take would do instead, including a human one.

## Running it

```bash
pip install numpy soundfile pyworld "setuptools<81" gradio_client
pip install --no-deps tinysoundfont
curl -L -o sf/GeneralUser.sf2 https://github.com/mrbumpy409/GeneralUser-GS/raw/main/GeneralUser-GS.sf2
```

ffmpeg on PATH. Python 3.14 on Windows works.

```bash
# 1–2. vocoder vocal + band (free; needs an OpenRouter key)
set OPENROUTER_API_KEY=sk-or-...
python sing.py ref/ref_clip.wav --tag mandy
python arrange.py out/seedvc_out_28s.wav out/auld_lang_syne_he_arranged.mp3 --tag mandy

# 3. ACE-Step cover, a cappella (your own Space, see below)
set ACE_URL=https://<you>-ace-step-v1-5.hf.space
set HF_TOKEN=hf_...
python acestep.py out/ace_acapella_70.mp3 --cover out/auld_lang_syne_he_arranged.mp3 --strength 0.7 ^
  --caption "a cappella, solo male baritone vocal only, no instruments, dry studio vocal, slow tender ballad, clear Hebrew diction, 80 bpm"
ffmpeg -i out/ace_acapella_70.mp3 -ac 1 -ar 44100 out/ace_acapella_70.wav

# 4. voice conversion (your own Space, see below)
set SEEDVC_URL=https://<you>-seed-vc.hf.space
python seedvc.py out/ace_acapella_70.wav ref/ref_clip_28s.wav out/ace_mandy.wav

# 5. mix over the band arrange.py already rendered
ffmpeg -i out/ace_mandy.wav -i out/mandy_band.wav -filter_complex "[0:a]aecho=0.9:0.3:60:0.12,pan=stereo|c0=c0|c1=c0[v];[1:a]volume=-6dB,aecho=0.8:0.5:110:0.22[b];[v][b]amix=inputs=2:duration=longest:normalize=0,loudnorm=I=-14:TP=-1.5" -b:a 192k out/ace_mandy_arranged.mp3
```

Another singer: a new reference clip and a new `--tag`. Jack Black was `--transpose -12`; the auto-transpose picked -17 for his low clone, which was too muddy.

## Hosting the GPU steps

Both models have free public Hugging Face Spaces, but they run on ZeroGPU with a small daily quota, and ACE-Step's cover mode crashes there (its audio encoder lands on CPU). Duplicate each Space into your account on paid hardware; both sleep after 15 minutes idle.

- **ACE-Step** on an Nvidia L4 or A10G small (24 GB, about $1/hour). Add a Space variable `SERVICE_MODE_DIT_MODEL_2` with a single-space value. The stock app loads two DiT models plus a 1.7B LM and runs out of memory otherwise.
- **Seed-VC** on a T4 small ($0.40/hour). Add `python_version: "3.10"` (quoted) to the README front matter. The default Python 3.13 has no scipy 1.13 wheel and the build fails.

The session that produced the final tracks cost about $2.

## Knobs

- `sing.py --tag NAME --bpm 80 --transpose -10 --seed 7`. Lyrics are `LINES` in the file; syllable counts must stay 8,6,8,6,8,6,8,6 to match the melody.
- `acestep.py --strength 0.5..0.85`. Higher tracks the source melody more tightly. `--model acestep-v15-turbo` for the 2B model on smaller cards.
- `arrange.py --band_db -6 --vocal_db 0 --intro 4`. Instrument levels and panning are the `VOLUME` / `PAN` dicts at the top.

## Also in here

Earlier rungs of the ladder, kept for reference: `auld_lang_syne_he.py` (one-shot TTS), `autotune.py` (scale snap, can't add a melody), `melodize.py` (force melody by phrase), `accomp.py` (sine-synth piano). Their outputs are `out/auld_lang_syne_he*.mp3` when run.

## Notes

The reference clips are short excerpts of public performances used purely as timbre references. The generated vocals are synthetic. Don't present them as the real singers.
