"""Load the newsletter registry and shared paths/settings."""
import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILE = ROOT / "config" / "newsletters.yml"
DATA_DIR = ROOT / "data"
STATE_FILE = DATA_DIR / "state.json"
SUMMARIES_DIR = DATA_DIR / "summaries"
SITE_DIR = ROOT / "docs"
TEMPLATES_DIR = ROOT / "templates"

TIMEZONE = "America/New_York"

# Models are user-approved plan choices; override via env if desired.
SUMMARIZE_MODEL = os.environ.get("SUMMARIZE_MODEL", "claude-haiku-4-5")
SYNTH_MODEL = os.environ.get("SYNTH_MODEL", "claude-sonnet-5")

# Inbox lookback windows, in hours.
LOOKBACK_HOURS = {"daily": 48, "weekly": 192}


@dataclass
class Newsletter:
    id: str
    name: str
    category: str
    batch: str
    cadence: str
    senders: list
    url: str
    subject_contains: list = field(default_factory=list)
    subject_excludes: list = field(default_factory=list)

    def matches(self, from_header: str, subject: str) -> bool:
        from_l = (from_header or "").lower()
        if not any(s.lower() in from_l for s in self.senders):
            return False
        subj_l = (subject or "").lower()
        if self.subject_contains and not any(s.lower() in subj_l for s in self.subject_contains):
            return False
        if self.subject_excludes and any(s.lower() in subj_l for s in self.subject_excludes):
            return False
        return True


@dataclass
class Batch:
    id: str
    deadline_et: str
    label: str
    newsletters: list


def load_config():
    """Return (batches: dict[str, Batch], newsletters: list[Newsletter])."""
    raw = yaml.safe_load(CONFIG_FILE.read_text(encoding="utf-8"))
    newsletters = [Newsletter(**n) for n in raw["newsletters"]]
    batches = {}
    for batch_id, meta in raw["batches"].items():
        batches[batch_id] = Batch(
            id=batch_id,
            deadline_et=meta["deadline_et"],
            label=meta["label"],
            newsletters=[n for n in newsletters if n.batch == batch_id],
        )
    return batches, newsletters
