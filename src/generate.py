#!/usr/bin/env python3
"""Weekly job: plan the next 7 days, draw cards, write copy, render media, add to queue."""
import argparse
import re
import shutil
import sys
from datetime import datetime, timedelta, time as dtime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).parent))
import cards as deck
import llm, render, video
from common import ROOT, load_config, load_queue, save_queue
from notify import notify

DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

SCHEMAS = {
    "reel": '{"hook": "max 12 words, scroll-stopping opener", "readings": [{"text": "25-35 words"}, ...one per card, in order], '
            '"cta": "max 15 words, ask viewer to save/follow/comment", "caption": "2-3 sentences", "hashtags": ["8 tags, no # sign"]}',
    "carousel": '{"title": "max 8 words", "slides": ["40-55 words on the card meaning", "40-55 words of practical advice ending with a reflection question"], '
                '"caption": "2-3 sentences", "hashtags": ["8 tags, no # sign"]}',
    "story": '{"line": "max 18 words, a gentle daily message"}',
}
TASKS = {
    "reel": "Write a short-form video script. If there are 3 cards, frame them as 'Pile 1/2/3' pick-a-pile readings; if 1 card, a card-of-the-day message.",
    "carousel": "Write a 3-slide educational Instagram carousel about the drawn card (slide 1 is the cover with the title).",
    "story": "Write a one-line card-of-the-day message for an Instagram story.",
}


def make_prompt(cfg, slot, drawn):
    cl = "\n".join(f"{i+1}. {deck.label(c)} - keywords: {c['keywords']}" for i, c in enumerate(drawn))
    return f"""You write content for a tarot reading Instagram page. Voice: {cfg['voice_style']}.
Rules: empowering and reflective, framed as guidance, never absolute. NEVER predict death, illness, pregnancy,
legal outcomes, or money/investment results. No fear-based language. No emojis in on-screen text.
Cards already drawn (do not change them):
{cl}
Task: {TASKS[slot['type']]}
Return ONLY JSON in exactly this shape: {SCHEMAS[slot['type']]}"""


def valid(slot, c, n):
    try:
        if slot["type"] == "reel":
            return (isinstance(c["hook"], str) and isinstance(c["cta"], str) and isinstance(c["caption"], str)
                    and len(c["readings"]) == n and all(isinstance(r["text"], str) for r in c["readings"]))
        if slot["type"] == "carousel":
            return isinstance(c["title"], str) and len(c["slides"]) == 2 and isinstance(c["caption"], str)
        return isinstance(c["line"], str)
    except (KeyError, TypeError):
        return False


def fallback(slot, drawn):
    """Template copy used when no Gemini key / quota exhausted / unsafe output."""
    def txt(c):
        return (f"{c['name']} brings the energy of {c['keywords']}. Sit with this today and notice "
                f"where it already shows up in your life.")
    if slot["type"] == "reel":
        return {"hook": "This message is for you today." if len(drawn) == 1 else "Pick a pile. Trust your first instinct.",
                "readings": [{"text": txt(c)} for c in drawn],
                "cta": "Save this and follow for your daily card.",
                "caption": "Take what resonates and leave the rest.", "hashtags": []}
    if slot["type"] == "carousel":
        c = drawn[0]
        return {"title": f"{c['name']}: what it means",
                "slides": [txt(c), f"Reflect: where is {c['keywords'].split(',')[0]} asking for your attention this week?"],
                "caption": f"Card spotlight: {deck.label(c)}.", "hashtags": []}
    return {"line": f"{drawn[0]['name']} today: {drawn[0]['keywords'].split(',')[0]}."}


def get_content(cfg, slot, drawn):
    for _ in range(3):
        c = llm.gemini_json(make_prompt(cfg, slot, drawn), cfg["gemini_model"])
        if c and valid(slot, c, len(drawn)) and llm.is_safe(c):
            return c
    print("Using fallback copy for", slot["name"])
    return fallback(slot, drawn)


def caption_text(cfg, c):
    tags = []
    for t in list(c.get("hashtags", [])) + cfg["base_hashtags"]:
        t = re.sub(r"[^A-Za-z0-9_]", "", str(t))
        if t and t.lower() not in [x.lower() for x in tags]:
            tags.append(t)
    tags = tags[: cfg["max_hashtags"]]
    return f"{c['caption'].strip()}\n\n{cfg['disclaimer']}\n\n" + " ".join("#" + t for t in tags)


def music_file():
    files = sorted(p for p in (ROOT / "assets" / "music").glob("*") if p.suffix.lower() in (".mp3", ".m4a", ".wav"))
    return files[0] if files else None


def build_item(cfg, slot, day, media_dir):
    drawn = deck.draw(slot["cards"], cfg["reversed_chance"])
    c = get_content(cfg, slot, drawn)
    item_id = f"{day.isoformat()}-{slot['name']}"
    brand = cfg["brand"]
    media = []
    rel = lambda p: Path(p).relative_to(ROOT).as_posix()

    if slot["type"] == "story":
        p = render.compose(media_dir / f"{item_id}.jpg", render.STORY, card=drawn[0],
                           title=deck.label(drawn[0]), body=c["line"], brand=brand)
        media, caption = [rel(p)], ""
    elif slot["type"] == "carousel":
        card, size, safe = drawn[0], render.FEED, (90, 110)
        s1 = render.compose(media_dir / f"{item_id}-1.jpg", size, card=card, title=c["title"], brand=brand, safe=safe, card_frac=0.62)
        s2 = render.compose(media_dir / f"{item_id}-2.jpg", size, title=deck.label(card), body=c["slides"][0], brand=brand, safe=safe, body_size=50)
        s3 = render.compose(media_dir / f"{item_id}-3.jpg", size, title="Reflect", body=c["slides"][1], brand=brand, safe=safe, body_size=50)
        media, caption = [rel(s1), rel(s2), rel(s3)], caption_text(cfg, c)
    else:  # reel
        work = ROOT / "work" / item_id
        frames = [(render.compose(work / "f0.jpg", render.STORY, back=True, body=c["hook"], brand=brand, card_frac=0.34, body_size=64), c["hook"])]
        for i, (card, r) in enumerate(zip(drawn, c["readings"])):
            pile = f"Pile {i+1}" if len(drawn) > 1 else None
            title = f"{pile}: {deck.label(card)}" if pile else deck.label(card)
            narr = (f"{pile}. " if pile else "") + f"{deck.spoken(card)}. {r['text']}"
            frames.append((render.compose(work / f"f{i+1}.jpg", render.STORY, card=card, title=title, body=r["text"], brand=brand, card_frac=0.34, body_size=46), narr))
        frames.append((render.compose(work / "fz.jpg", render.STORY, back=True, title=brand, body=c["cta"], card_frac=0.3, body_size=60), c["cta"]))
        out = video.build_reel(frames, cfg["voice"], media_dir / f"{item_id}.mp4", work, music_file())
        shutil.rmtree(work, ignore_errors=True)
        media, caption = [rel(out)], caption_text(cfg, c)

    tz = ZoneInfo(cfg["timezone"])
    hh, mm = map(int, slot["time"].split(":"))
    when = datetime.combine(day, dtime(hh, mm), tz).astimezone(timezone.utc)
    return {"id": item_id, "type": slot["type"], "publish_at": when.isoformat(), "status": "scheduled",
            "attempts": 0, "caption": caption, "media": media,
            "cards": [deck.label(x) for x in drawn]}


def slot_matches(slot, day):
    days = slot["days"]
    return "daily" in days or DAYS[day.weekday()] in days


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="render one of each slot into ./preview, don't touch the queue")
    args = ap.parse_args()
    cfg = load_config()

    if args.dry_run:
        out = ROOT / "preview"
        shutil.rmtree(out, ignore_errors=True)
        day = datetime.now(ZoneInfo(cfg["timezone"])).date() + timedelta(days=1)
        for slot in cfg["slots"]:
            item = build_item(cfg, slot, day, out)
            print(item["id"], item["cards"], item["media"])
            print(item["caption"][:300], "\n")
        return

    queue = load_queue()
    have = {i["id"] for i in queue}
    now = datetime.now(ZoneInfo(cfg["timezone"]))
    added = 0
    for offset in range(1, 8):
        day = (now + timedelta(days=offset)).date()
        for slot in cfg["slots"]:
            iid = f"{day.isoformat()}-{slot['name']}"
            if not slot_matches(slot, day) or iid in have:
                continue
            try:
                queue.append(build_item(cfg, slot, day, ROOT / "media"))
                save_queue(queue)
                added += 1
            except Exception as e:
                notify(f"Failed to build {iid}: {e}")
    notify(f"Weekly planning done: {added} new items queued.")


if __name__ == "__main__":
    main()
