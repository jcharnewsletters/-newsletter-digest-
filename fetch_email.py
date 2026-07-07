"""Fetch the latest issue of each newsletter in a batch.

Two modes:
  * live  — IMAP against the dedicated Gmail inbox (GMAIL_ADDRESS / GMAIL_APP_PASSWORD)
  * fixtures — load sample issues from tests/fixtures/<batch>.json (no credentials)
"""
import email
import email.policy
import imaplib
import json
import os
from datetime import timedelta
from pathlib import Path

from .common import batch_newsletters, now_et

IMAP_HOST = "imap.gmail.com"
LOOKBACK_HOURS = 26  # catch anything since yesterday's run


def _matches(nl: dict, from_header: str, subject: str) -> bool:
    frm, subj = from_header.lower(), subject.lower()
    if not any(p.lower() in frm for p in nl["senders"]):
        return False
    for p in nl.get("subject_contains", []):
        if p.lower() not in subj:
            return False
    for p in nl.get("subject_not_contains", []):
        if p.lower() in subj:
            return False
    return True


def _best_body(msg) -> tuple[str, str]:
    """Return (html, plain) — whichever parts exist."""
    html, plain = "", ""
    for part in msg.walk():
        ctype = part.get_content_type()
        if part.get_content_disposition() == "attachment":
            continue
        try:
            payload = part.get_content()
        except Exception:
            continue
        if ctype == "text/html" and not html:
            html = payload
        elif ctype == "text/plain" and not plain:
            plain = payload
    return html, plain


def fetch_live(cfg: dict, batch: str) -> list[dict]:
    address = os.environ["GMAIL_ADDRESS"]
    password = os.environ["GMAIL_APP_PASSWORD"]
    since = (now_et() - timedelta(hours=LOOKBACK_HOURS)).strftime("%d-%b-%Y")

    issues: dict[str, dict] = {}
    with imaplib.IMAP4_SSL(IMAP_HOST) as imap:
        imap.login(address, password)
        imap.select("INBOX", readonly=True)
        _, data = imap.search(None, f'(SINCE "{since}")')
        ids = data[0].split()
        for mid in reversed(ids):  # newest first
            _, msg_data = imap.fetch(mid, "(RFC822)")
            msg = email.message_from_bytes(msg_data[0][1], policy=email.policy.default)
            frm = msg.get("From", "")
            subj = msg.get("Subject", "")
            for nl in batch_newsletters(cfg, batch):
                if nl["name"] not in issues and _matches(nl, frm, subj):
                    html, plain = _best_body(msg)
                    issues[nl["name"]] = {
                        "newsletter": nl["name"],
                        "cadence": nl["cadence"],
                        "subject": subj,
                        "from": frm,
                        "html": html,
                        "plain": plain,
                    }
    return list(issues.values())


def fetch_fixtures(cfg: dict, batch: str, fixtures_dir: str) -> list[dict]:
    path = Path(fixtures_dir) / f"{batch}.json"
    if not path.exists():
        raise SystemExit(f"No fixture file at {path}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    names = {n["name"]: n for n in batch_newsletters(cfg, batch)}
    out = []
    for item in raw:
        nl = names.get(item["newsletter"])
        if nl:
            item.setdefault("cadence", nl["cadence"])
            item.setdefault("plain", "")
            out.append(item)
    return out


def fetch(cfg: dict, batch: str, fixtures_dir: str | None = None) -> list[dict]:
    if fixtures_dir:
        return fetch_fixtures(cfg, batch, fixtures_dir)
    return fetch_live(cfg, batch)
