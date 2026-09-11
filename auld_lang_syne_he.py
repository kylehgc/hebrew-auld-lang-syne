"""Clone a voice from a clip and speak Auld Lang Syne in Hebrew via OpenRouter's free Fish Audio model.

usage: python auld_lang_syne_he.py voice_clip.wav [out.mp3]
needs: OPENROUTER_API_KEY env var. Clip: 10-30 s, wav or mp3, one speaker, no music.
"""
import base64, json, os, sys, urllib.request

LYRICS_HE = """\
הֲיִשָּׁכְחוּ יְדִידִים מִכְּבָר,
וְלֹא יַעֲלוּ עוֹד עַל הַלֵּב?
הֲיִשָּׁכְחוּ יְדִידִים מִכְּבָר,
וִימֵי הַזְּמַן שֶׁחָלַף?

לְזֵכֶר הַיָּמִים שֶׁחָלְפוּ, יְדִידִי,
לְזֵכֶר הַיָּמִים שֶׁחָלְפוּ,
נָרִים עוֹד כּוֹס שֶׁל טוּב לֵבָב,
לְזֵכֶר הַיָּמִים שֶׁחָלְפוּ.
"""

clip, out = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else "auld_lang_syne_he.mp3")
mime = "audio/mpeg" if clip.lower().endswith(".mp3") else "audio/wav"
with open(clip, "rb") as f:
    ref = f"data:{mime};base64,{base64.b64encode(f.read()).decode()}"

body = {
    "model": "fish-audio/s2.1-pro-free:free",
    "input": LYRICS_HE,
    "response_format": "mp3",
    "input_references": [{"type": "input_audio", "input_audio": {"data": ref}}],
}
req = urllib.request.Request(
    "https://openrouter.ai/api/v1/audio/speech",
    data=json.dumps(body).encode(),
    headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}", "Content-Type": "application/json"},
)
with urllib.request.urlopen(req) as r, open(out, "wb") as f:
    f.write(r.read())
print("wrote", out)
