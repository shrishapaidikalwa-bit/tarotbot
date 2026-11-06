#!/usr/bin/env python3
"""Hourly job: publish anything that is due, retry on failure, alert, clean up old media."""
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
from common import ROOT, load_config, load_queue, save_queue
from instagram import IG
from notify import notify


def media_url(cfg, path):
    """Instagram must fetch media from a public URL. Try jsDelivr (correct MIME types), then raw GitHub."""
    repo, branch = os.environ["GITHUB_REPOSITORY"], cfg.get("branch", "main")
    for u in (f"https://cdn.jsdelivr.net/gh/{repo}@{branch}/{path}",
              f"https://raw.githubusercontent.com/{repo}/{branch}/{path}"):
        try:
            if requests.head(u, allow_redirects=True, timeout=30).status_code == 200:
                return u
        except requests.RequestException:
            pass
    raise RuntimeError(f"media not publicly reachable yet: {path}")


def post(ig, cfg, it):
    urls = [media_url(cfg, p) for p in it["media"]]
    if it["type"] == "reel":
        return ig.reel(urls[0], it["caption"])
    if it["type"] == "carousel":
        return ig.carousel(urls, it["caption"])
    return ig.story(urls[0])


def cleanup(queue):
    cutoff = datetime.now(timezone.utc) - timedelta(days=3)
    for it in queue:
        if it["status"] in ("posted", "failed", "missed") and not it.get("media_deleted") \
                and datetime.fromisoformat(it["publish_at"]) < cutoff:
            for p in it["media"]:
                (ROOT / p).unlink(missing_ok=True)
            it["media_deleted"] = True
    # keep queue.json small: drop records older than 30 days
    keep = datetime.now(timezone.utc) - timedelta(days=30)
    queue[:] = [i for i in queue if datetime.fromisoformat(i["publish_at"]) > keep]


def main():
    cfg, queue = load_config(), load_queue()
    ig = IG(os.environ["IG_USER_ID"], os.environ["IG_ACCESS_TOKEN"], cfg["graph_version"])
    now = datetime.now(timezone.utc)
    for it in queue:
        if it["status"] != "scheduled":
            continue
        due = datetime.fromisoformat(it["publish_at"])
        if due > now:
            continue
        if now - due > timedelta(hours=36):
            it["status"] = "missed"
            notify(f"Missed (too late to post): {it['id']}")
            save_queue(queue)
            continue
        try:
            it["ig_id"] = post(ig, cfg, it)
            it["status"], it["posted_at"] = "posted", now.isoformat()
            print("Posted", it["id"], it["ig_id"])
        except Exception as e:
            it["attempts"] += 1
            it["last_error"] = str(e)[:500]
            print("Error", it["id"], e)
            if it["attempts"] >= cfg["max_attempts"]:
                it["status"] = "failed"
                notify(f"FAILED after {it['attempts']} attempts: {it['id']} - {str(e)[:200]}")
        save_queue(queue)  # save immediately so a crash can never cause a double-post
        time.sleep(20)
    cleanup(queue)
    save_queue(queue)


if __name__ == "__main__":
    main()
