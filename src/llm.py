"""Free-tier Gemini for writing. Falls back to templates if no key / any failure."""
import json
import os
import re
import time
import requests

# Things a tarot page should never automatically publish.
BLOCK = re.compile(
    r"you (will|are going to) (die|get sick|lose your|be diagnosed)|diagnos|cancer|pregnan|"
    r"lawsuit|sue |invest in|buy (stocks?|crypto|bitcoin)|stop taking|medication|"
    r"suicid|self-harm|curse|doomed|guaranteed", re.I)

_DISABLED = False


def gemini_json(prompt, model):
    global _DISABLED
    key = os.environ.get("GEMINI_API_KEY")
    if not key or _DISABLED:
        return None
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json", "temperature": 0.95}}
    for i in range(3):
        try:
            r = requests.post(url, headers={"x-goog-api-key": key}, json=body, timeout=60)
            if r.status_code == 200:
                text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                out = json.loads(text)
                time.sleep(7)  # stay under the free-tier requests-per-minute limit
                return out
            print("Gemini status", r.status_code, r.text[:300])
            if r.status_code in (400, 401, 403, 404):
                _DISABLED = True  # bad key / bad model name: stop retrying for this run
                return None
        except Exception as e:
            print("Gemini error:", e)
        time.sleep(5 * (i + 1))
    return None


def _strings(o):
    if isinstance(o, str):
        yield o
    elif isinstance(o, dict):
        for v in o.values():
            yield from _strings(v)
    elif isinstance(o, list):
        for v in o:
            yield from _strings(v)


def is_safe(content):
    return not any(BLOCK.search(s) for s in _strings(content))
