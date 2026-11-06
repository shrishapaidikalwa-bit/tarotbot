# Tarot Instagram Autopilot ($0 stack)

GitHub Actions (scheduler + free hosting) → Gemini free tier (copy) → edge-tts (voice) → FFmpeg/Pillow (render) → Instagram Graph API (publish).

- **Sunday**: plans the next 7 days, draws cards with a real random function, writes copy, renders reels / carousels / stories, commits them to the repo.
- **Every hour**: publishes whatever is due, retries 3x, alerts you on failure, deletes old media.
- Schedule and branding live in `config.yaml`.

## One-time setup (~45 min)

### 1. GitHub repo (must be PUBLIC)
Instagram has to download media from a public URL, and GitHub is the free host. Create a **public** repo, push this folder to it. Secrets stay in GitHub Secrets, never in code.
Settings → Actions → General → Workflow permissions → **Read and write**.

### 2. Instagram / Meta
1. Switch Instagram to a **Professional** account and link it to a **Facebook Page**.
2. developers.facebook.com → Create App (type Business) → add **Instagram Graph API** (or "Facebook Login for Business"). Keep it in Development mode; you're the admin so no app review is needed.
3. Graph API Explorer → select your app → generate a User token with `instagram_basic`, `instagram_content_publish`, `pages_show_list`, `pages_read_engagement` (add `business_management` if Meta asks).
4. Exchange for a long-lived user token:
   `https://graph.facebook.com/v23.0/oauth/access_token?grant_type=fb_exchange_token&client_id=APP_ID&client_secret=APP_SECRET&fb_exchange_token=SHORT_TOKEN`
5. Get your **Page token** (derived from a long-lived user token, it does not expire, so no refresh job is needed):
   `https://graph.facebook.com/v23.0/me/accounts?access_token=LONG_USER_TOKEN` → copy the Page's `access_token`.
6. Get your IG user id:
   `https://graph.facebook.com/v23.0/PAGE_ID?fields=instagram_business_account&access_token=PAGE_TOKEN`

### 3. Gemini (free)
Create a key at aistudio.google.com/apikey (no card needed). Without it the bot still runs on template copy, but it will be bland.

### 4. GitHub secrets (Settings → Secrets and variables → Actions)
| Secret | Value |
|---|---|
| `IG_USER_ID` | from step 2.6 |
| `IG_ACCESS_TOKEN` | Page token from step 2.5 |
| `GEMINI_API_KEY` | from step 3 |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | optional failure alerts (create a bot with @BotFather, free) |

### 5. Assets (optional but recommended)
- `assets/cards/` : Rider-Waite-Smith card images named by slug, e.g. `the-fool.jpg`, `ace-of-wands.jpg`, `queen-of-pentacles.jpg`. The 1909 deck is public domain in the US (scans are on Wikimedia Commons; check each file's license). Missing cards get a styled placeholder, so nothing breaks.
- `assets/music/` : one royalty-free mp3 (it's mixed quietly under the voice). Use only tracks you have the rights to.
- `assets/fonts/title.ttf` and `body.ttf` : your own fonts, optional.
- Edit `config.yaml`: `brand`, `timezone`, `branch`, schedule.

### 6. Test, then forget it
1. Locally: `pip install -r requirements.txt && python src/generate.py --dry-run` → check `preview/`.
2. GitHub → Actions → **Weekly content generation** → Run workflow. Wait for the commit.
3. Actions → **Hourly publisher** → Run workflow (posts anything already due). Check Instagram.
After that it runs by itself.

## Honest limitations
- **Stories** are image-only: the API can't add polls/question stickers or music.
- GitHub cron can run 5-30 min late; posts go out at the first hourly run after their time.
- edge-tts is an unofficial free endpoint. If it's down, the bot falls back to silent, text-only reels instead of failing.
- Gemini free tier has rate limits and its terms allow Google to use free-tier data. Fine for tarot copy, not for anything private.
- If the repo has no activity for 60 days GitHub pauses schedules; the weekly commits normally prevent that.
- Fully automated, repetitive content can get reduced reach. Rotate your card art, music and wording, and glance at the page occasionally.
- If a Graph API version is retired, change `graph_version` in `config.yaml`.
- No analytics feedback loop is included yet.
