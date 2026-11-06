"""Image rendering with Pillow. Card art is optional: a styled placeholder is drawn if missing."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps
from common import ROOT

GOLD, CREAM = (226, 190, 110), (245, 238, 255)
DEEP, MID, CARDBG = (18, 9, 38), (62, 30, 104), (34, 17, 66)

STORY = (1080, 1920)
FEED = (1080, 1350)

_FONT_CANDIDATES = {
    True: ["title.ttf", "DejaVuSerif-Bold.ttf", "LiberationSerif-Bold.ttf"],
    False: ["body.ttf", "DejaVuSerif.ttf", "LiberationSerif-Regular.ttf"],
}
_FONT_DIRS = [ROOT / "assets" / "fonts", Path("/usr/share/fonts/truetype/dejavu"),
              Path("/usr/share/fonts/truetype/liberation"), Path("/usr/share/fonts/dejavu")]


def font(size, bold=False):
    for name in _FONT_CANDIDATES[bold]:
        for d in _FONT_DIRS:
            p = d / name
            if p.exists():
                return ImageFont.truetype(str(p), size)
    return ImageFont.load_default(size)


def gradient(w, h):
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = 1 - abs(2 * y / h - 1)
        d.line([(0, y), (w, y)], fill=tuple(int(DEEP[i] + (MID[i] - DEEP[i]) * t) for i in range(3)))
    # sparse "stars"
    import random
    rnd = random.Random(7)
    for _ in range(90):
        x, y, r = rnd.randrange(w), rnd.randrange(h), rnd.choice([1, 1, 2, 3])
        d.ellipse([x - r, y - r, x + r, y + r], fill=(230, 220, 255))
    return img


def wrap(text, f, max_w):
    lines, cur = [], ""
    for word in text.split():
        t = (cur + " " + word).strip()
        if f.getlength(t) <= max_w:
            cur = t
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def text_block(d, text, bold, start, min_size, color, w, y, max_h, margin=90):
    """Centered, wrapped text that shrinks until it fits max_h. Returns y after block."""
    size = start
    while True:
        f = font(size, bold)
        lines = wrap(text, f, w - 2 * margin)
        lh = int(size * 1.3)
        if len(lines) * lh <= max_h or size <= min_size:
            break
        size -= 2
    for ln in lines:
        d.text((w / 2, y), ln, font=f, fill=color, anchor="ma")
        y += lh
    return y


def star(d, cx, cy, r, fill):
    k = r * 0.25
    d.polygon([(cx, cy - r), (cx + k, cy - k), (cx + r, cy), (cx + k, cy + k), (cx, cy + r),
               (cx - k, cy + k), (cx - r, cy), (cx - k, cy - k)], fill=fill)


def find_card_file(card):
    for ext in ("jpg", "jpeg", "png", "webp"):
        p = ROOT / "assets" / "cards" / f"{card['slug']}.{ext}"
        if p.exists():
            return p


def card_back(height):
    w = int(height * 0.6)
    im = Image.new("RGBA", (w, height), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, height - 1], 24, fill=CARDBG, outline=GOLD, width=8)
    cx, cy = w // 2, height // 2
    for r in (0.38, 0.28, 0.18):
        rr = int(w * r)
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=GOLD, width=3)
    star(d, cx, cy, int(w * 0.16), GOLD)
    return im


def placeholder(card, height):
    w = int(height * 0.6)
    im = Image.new("RGBA", (w, height), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, height - 1], 24, fill=CARDBG, outline=GOLD, width=8)
    d.rounded_rectangle([20, 20, w - 21, height - 21], 16, outline=GOLD, width=2)
    star(d, w // 2, int(height * 0.2), int(w * 0.12), GOLD)
    y = int(height * 0.38)
    y = text_block(d, card["name"], True, int(w * 0.14), 20, GOLD, w, y, int(height * 0.3), margin=30)
    if card["reversed"]:
        d.text((w / 2, y + 10), "REVERSED", font=font(int(w * 0.07), True), fill=CREAM, anchor="ma")
    return im


def card_art(card, height):
    f = find_card_file(card)
    if not f:
        return placeholder(card, height)
    im = Image.open(f).convert("RGB")
    im = im.resize((int(im.width * height / im.height), height), Image.LANCZOS)
    im = ImageOps.expand(im, border=8, fill=GOLD)
    if card["reversed"]:
        im = im.rotate(180)
    return im.convert("RGBA")


def compose(path, size, card=None, back=False, title=None, body=None, brand=None,
            safe=(250, 340), card_frac=0.4, body_size=56):
    w, h = size
    img = gradient(w, h)
    d = ImageDraw.Draw(img)
    top, bottom = safe[0], h - safe[1]
    y = top
    if card or back:
        art = card_art(card, int((bottom - top) * card_frac)) if card else card_back(int((bottom - top) * card_frac))
        img.paste(art, ((w - art.width) // 2, y), art)
        y += art.height + 40
    else:
        y += 120
    if title:
        y = text_block(d, title, True, 68, 36, GOLD, w, y, 220) + 18
    if body:
        text_block(d, body, False, body_size, 30, CREAM, w, y, max(bottom - y - 70, 100))
    if brand:
        d.text((w / 2, bottom - 20), brand, font=font(34), fill=GOLD, anchor="ma")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "JPEG", quality=93)  # Instagram feed only accepts JPEG
    return path
