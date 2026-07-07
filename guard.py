"""Decide which batch (if any) is due right now — the DST-safe guard.

The workflow has TWO cron entries per batch (one for EDT, one for EST).
Whichever fires, this guard converts "now" to Eastern Time and only approves
a batch whose run_at is within ±25 minutes AND that hasn't already been sent
today. The wrong-offset cron lands 60 minutes off, so it is always rejected:
no missed batches, no double-fires, across every daylight-saving change.

Prints the batch name to stdout (and to $GITHUB_OUTPUT as batch=<name>),
or "none".
"""
import os

from .common import load_config, load_state, now_et


def due_batch() -> str:
    cfg = load_config()
    state = load_state()
    now = now_et()
    today = now.strftime("%Y-%m-%d")
    minutes_now = now.hour * 60 + now.minute
    weekday = now.weekday() < 5

    for name, b in cfg["batches"].items():
        h, m = map(int, b["run_at"].split(":"))
        if abs(minutes_now - (h * 60 + m)) > 25:
            continue
        if b.get("days") == "weekdays" and not weekday:
            continue
        if state["last_sent"].get(name) == today:
            continue
        return name
    return "none"


if __name__ == "__main__":
    batch = due_batch()
    print(batch)
    gh_out = os.environ.get("GITHUB_OUTPUT")
    if gh_out:
        with open(gh_out, "a", encoding="utf-8") as f:
            f.write(f"batch={batch}\n")
