import time
import requests


class IG:
    """Publishes through Meta's Instagram API.
    api="instagram": Instagram Login, no Facebook Page needed (graph.instagram.com, account id "me").
    api="facebook":  the older Facebook Page flow (graph.facebook.com, explicit IG user id)."""

    def __init__(self, user_id, token, version, api="instagram"):
        self.token = token
        if api == "facebook":
            self.host, self.uid = "https://graph.facebook.com", user_id
        else:
            self.host, self.uid = "https://graph.instagram.com", "me"
        self.base = f"{self.host}/{version}"

    def _post(self, path, **data):
        r = requests.post(f"{self.base}/{path}", data={**data, "access_token": self.token}, timeout=90)
        if not r.ok:
            raise RuntimeError(f"Graph API {r.status_code}: {r.text[:400]}")
        return r.json()

    def _wait(self, cid, tries=60):
        for _ in range(tries):
            r = requests.get(f"{self.base}/{cid}", params={"fields": "status_code,status", "access_token": self.token}, timeout=60)
            s = r.json().get("status_code")
            if s == "FINISHED":
                return
            if s in ("ERROR", "EXPIRED"):
                raise RuntimeError(f"Container {s}: {r.text[:300]}")
            time.sleep(10)
        raise RuntimeError("Timed out waiting for media processing")

    def _publish(self, cid):
        self._wait(cid)
        return self._post(f"{self.uid}/media_publish", creation_id=cid)["id"]

    def reel(self, video_url, caption):
        cid = self._post(f"{self.uid}/media", media_type="REELS", video_url=video_url,
                         caption=caption, share_to_feed="true")["id"]
        return self._publish(cid)

    def story(self, image_url):
        cid = self._post(f"{self.uid}/media", media_type="STORIES", image_url=image_url)["id"]
        return self._publish(cid)

    def carousel(self, image_urls, caption):
        kids = []
        for u in image_urls:
            kid = self._post(f"{self.uid}/media", image_url=u, is_carousel_item="true")["id"]
            self._wait(kid)
            kids.append(kid)
        cid = self._post(f"{self.uid}/media", media_type="CAROUSEL", children=",".join(kids), caption=caption)["id"]
        return self._publish(cid)
