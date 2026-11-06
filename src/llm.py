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


def gemini_json(prompt, model):
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        return None
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json", "temperature": 0.95}}
    for i in range(3):
        try:
            r = requests.post(url, headers={"x-goog-api-key": key}, json=body, timeout=90)
            if r.status_code == 200:
                text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                return json.loads(text)
            print("Gemini status", r.status_code, r.text[:200])
        except Exception as e:  # network / parse errors
            print("Gemini error:", e)
        time.sleep(8 * (i + 1))
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
