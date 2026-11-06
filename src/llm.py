"""Free-tier Gemini for writing, with model fallback and fast give-up."""
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

# Tried in order after the model set in config.yaml.
FALLBACKS = ["gemini-3.1-flash-lite", "gemini-3.6-flash", "gemini-3.8-flash"]
_dead = set()  # models that failed during this run; not retried again


def gemini_json(prompt, model):
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        return None
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json", "temperature": 0.95}}
    for m in [model] + [x for x in FALLBACKS if x != model]:
        if m in _dead:
            continue
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent"
        for _ in range(2):
            try:
                r = requests.post(url, headers={"x-goog-api-key": key}, json=body, timeout=25)
            except Exception as e:
                print("Gemini", m, "error:", type(e).__name__)
                continue
            if r.status_code == 200:
                try:
                    text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                    out = json.loads(text)
                    time.sleep(5)  # gentle pacing for free-tier limits
                    return out
                except Exception:
                    print("Gemini", m, "returned unusable JSON")
                    continue
            print("Gemini", m, r.status_code, r.text[:100].replace("\n", " "))
            if r.status_code in (400, 401, 403, 404, 429):
                break  # quota / bad model: no point retrying this model
            time.sleep(3)
        _dead.add(m)
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
