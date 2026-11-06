import json
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
QUEUE = ROOT / "queue.json"


def load_config():
    return yaml.safe_load((ROOT / "config.yaml").read_text())


def load_queue():
    return json.loads(QUEUE.read_text() or "[]")


def save_queue(q):
    QUEUE.write_text(json.dumps(q, indent=2, ensure_ascii=False))
