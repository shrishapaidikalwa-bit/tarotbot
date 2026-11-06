import random
import re

_R = random.SystemRandom()

MAJORS = [
    ("The Fool", "new beginnings, trust, a leap of faith", "recklessness, hesitation"),
    ("The Magician", "willpower, skill, manifestation", "scattered energy, untapped potential"),
    ("The High Priestess", "intuition, mystery, inner knowing", "ignoring your gut, hidden things"),
    ("The Empress", "nurturing, abundance, creativity", "creative block, overgiving"),
    ("The Emperor", "structure, authority, stability", "rigidity, control issues"),
    ("The Hierophant", "tradition, guidance, learning", "breaking convention, rebellion"),
    ("The Lovers", "connection, alignment, choices", "disharmony, misaligned values"),
    ("The Chariot", "determination, drive, victory", "lack of direction, scattered focus"),
    ("Strength", "courage, compassion, patience", "self-doubt, raw emotion"),
    ("The Hermit", "solitude, reflection, wisdom", "isolation, withdrawal"),
    ("Wheel of Fortune", "cycles, change, turning points", "resisting change, setbacks"),
    ("Justice", "fairness, truth, accountability", "unfairness, avoiding accountability"),
    ("The Hanged Man", "surrender, new perspective, pause", "stalling, needless sacrifice"),
    ("Death", "endings, transformation, release", "resisting change, clinging on"),
    ("Temperance", "balance, moderation, harmony", "excess, imbalance"),
    ("The Devil", "attachment, shadow, temptation", "release, breaking free"),
    ("The Tower", "sudden change, upheaval, revelation", "avoiding disaster, fear of change"),
    ("The Star", "hope, healing, renewal", "discouragement, lost faith"),
    ("The Moon", "illusion, intuition, uncertainty", "clarity emerging, releasing fear"),
    ("The Sun", "joy, vitality, success", "temporary clouds, dimmed optimism"),
    ("Judgement", "reflection, awakening, a reckoning", "self-doubt, ignoring the call"),
    ("The World", "completion, wholeness, achievement", "unfinished business, delays"),
]

SUITS = {
    "Wands": "passion and action",
    "Cups": "emotion and relationships",
    "Swords": "thought and conflict",
    "Pentacles": "work and the material world",
}
RANKS = [
    ("Ace", "a fresh start"), ("Two", "balance and choice"), ("Three", "growth and collaboration"),
    ("Four", "stability and pause"), ("Five", "conflict and challenge"), ("Six", "harmony and progress"),
    ("Seven", "reflection and perseverance"), ("Eight", "movement and mastery"),
    ("Nine", "resilience, nearly there"), ("Ten", "culmination and completion"),
    ("Page", "curiosity and messages"), ("Knight", "pursuit and momentum"),
    ("Queen", "nurturing inner mastery"), ("King", "authority and command"),
]


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _build():
    deck = [(n, u, r) for n, u, r in MAJORS]
    for suit, domain in SUITS.items():
        for rank, kw in RANKS:
            deck.append((f"{rank} of {suit}", f"{kw} in {domain}",
                         f"blocked or delayed {domain}, time to reassess"))
    return deck


DECK = _build()  # 78 cards


def draw(n, reversed_chance=0.3):
    picks = _R.sample(DECK, n)
    out = []
    for name, up, rev in picks:
        is_rev = _R.random() < reversed_chance
        out.append({"name": name, "slug": slug(name), "reversed": is_rev,
                    "keywords": rev if is_rev else up})
    return out


def label(c):
    return c["name"] + (" (Reversed)" if c["reversed"] else "")


def spoken(c):
    return c["name"] + (", reversed" if c["reversed"] else "")
