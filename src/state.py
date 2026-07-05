"""Persistent pipeline state: which emails were processed, when each batch last ran.

Stored as data/state.json and committed back to the repo by the workflow, so
reruns never double-process an issue or double-send an alert.
"""
import json
from datetime import datetime, timedelta, timezone

from .config import STATE_FILE

_EMPTY = {"processed_message_ids": {}, "batch_last_run": {}}
_RETENTION_DAYS = 30


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return json.loads(json.dumps(_EMPTY))


def save_state(state: dict) -> None:
    _prune(state)
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")


def is_processed(state: dict, message_id: str) -> bool:
    return message_id in state["processed_message_ids"]


def mark_processed(state: dict, message_id: str) -> None:
    state["processed_message_ids"][message_id] = datetime.now(timezone.utc).isoformat()


def batch_ran_on(state: dict, batch_id: str, date_str: str) -> bool:
    return state["batch_last_run"].get(batch_id) == date_str


def mark_batch_run(state: dict, batch_id: str, date_str: str) -> None:
    state["batch_last_run"][batch_id] = date_str


def _prune(state: dict) -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(days=_RETENTION_DAYS)
    keep = {}
    for mid, ts in state["processed_message_ids"].items():
        try:
            if datetime.fromisoformat(ts) >= cutoff:
                keep[mid] = ts
        except ValueError:
            pass
    state["processed_message_ids"] = keep
