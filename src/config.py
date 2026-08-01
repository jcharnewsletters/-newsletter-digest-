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

# Models. Cheap Haiku does the bulk per-newsletter summaries; Opus 5 does the
# one cross-newsletter merge per batch. Override via the SUMMARIZE_MODEL /
# SYNTH_MODEL env vars (wired to GitHub repo variables in the workflow) — the
# `or` fallback means an unset/empty variable uses these defaults.
SUMMARIZE_MODEL = os.environ.get("SUMMARIZE_MODEL") or "claude-haiku-4-5"
SYNTH_MODEL = os.environ.get("SYNTH_MODEL") or "claude-opus-5"

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
    # {header_name: substring} — used to split newsletters that share a From
    # address and have teaser subjects (e.g. the TLDR feeds, told apart by the
    # list id in their List-Unsubscribe header). ALL listed headers must match.
    header_contains: dict = field(default_factory=dict)
    # "HH:MM" (ET) — only accept issues that arrived BEFORE this time of day.
    # Used to keep a morning edition and drop a same-publisher evening edition
    # (e.g. Investopedia Pre-Market vs its evening send). Empty = no limit.
    arrives_before: str = ""

    def matches(self, from_header: str, subject: str, headers: dict = None) -> bool:
        from_l = (from_header or "").lower()
        if not any(s.lower() in from_l for s in self.senders):
            return False
        subj_l = (subject or "").lower()
        if self.subject_contains and not any(s.lower() in subj_l for s in self.subject_contains):
            return False
        if self.subject_excludes and any(s.lower() in subj_l for s in self.subject_excludes):
            return False
        if self.header_contains:
            headers = headers or {}
            for name, needle in self.header_contains.items():
                if needle.lower() not in headers.get(name.lower(), "").lower():
                    return False
        return True


def header_map(msg) -> dict:
    """Flatten an imap_tools message's headers into {lowercase_name: value}."""
    out = {}
    for key, val in (getattr(msg, "headers", None) or {}).items():
        joined = " ".join(val) if isinstance(val, (list, tuple)) else (val or "")
        out[key.lower()] = joined
    return out


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
