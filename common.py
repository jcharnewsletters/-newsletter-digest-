"""Shared helpers: config loading, paths, ET time."""
import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config" / "newsletters.yml"
DATA = ROOT / "data"
DIGESTS = DATA / "digests"
DOCS = ROOT / "docs"
STATE = DATA / "state.json"
ET = ZoneInfo("America/New_York")


def load_config() -> dict:
    with open(CONFIG, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def batch_newsletters(cfg: dict, batch: str) -> list[dict]:
    return [n for n in cfg["newsletters"] if n["batch"] == batch]


def now_et() -> datetime:
    return datetime.now(ET)


def load_state() -> dict:
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {"last_sent": {}}


def save_state(state: dict) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def stub_mode() -> bool:
    return os.environ.get("DIGEST_STUB_LLM", "").strip() in ("1", "true", "yes")
