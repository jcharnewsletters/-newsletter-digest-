"""Fetch new newsletter issues from the dedicated Gmail inbox over IMAP.

Auth uses a Gmail *app password* (a 16-character password Google issues for a
single app once 2-step verification is on), supplied via env vars:
  GMAIL_ADDRESS, GMAIL_APP_PASSWORD
"""
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from imap_tools import MailBox, AND

from . import state as state_mod
from .clean import html_to_text
from .config import LOOKBACK_HOURS

IMAP_HOST = "imap.gmail.com"


@dataclass
class Issue:
    newsletter_id: str
    newsletter_name: str
    message_id: str
    subject: str
    date: str  # ISO 8601
    text: str  # cleaned body


def fetch_issues(newsletters, state) -> list:
    """Return unprocessed Issues for the given newsletters, oldest first."""
    address = os.environ["GMAIL_ADDRESS"]
    password = os.environ["GMAIL_APP_PASSWORD"]

    max_lookback = max(LOOKBACK_HOURS[n.cadence] for n in newsletters)
    since = (datetime.now(timezone.utc) - timedelta(hours=max_lookback)).date()

    issues = []
    with MailBox(IMAP_HOST).login(address, password, initial_folder="INBOX") as mailbox:
        for msg in mailbox.fetch(AND(date_gte=since), mark_seen=False, bulk=True):
            newsletter = _match(newsletters, msg.from_, msg.subject)
            if newsletter is None:
                continue
            message_id = msg.headers.get("message-id", (msg.uid,))[0].strip()
            if state_mod.is_processed(state, message_id):
                continue
            msg_dt = msg.date
            if msg_dt.tzinfo is None:
                msg_dt = msg_dt.replace(tzinfo=timezone.utc)
            age_hours = (datetime.now(timezone.utc) - msg_dt).total_seconds() / 3600
            if age_hours > LOOKBACK_HOURS[newsletter.cadence]:
                continue
            body = msg.html or msg.text or ""
            issues.append(Issue(
                newsletter_id=newsletter.id,
                newsletter_name=newsletter.name,
                message_id=message_id,
                subject=msg.subject or "(no subject)",
                date=msg_dt.isoformat(),
                text=html_to_text(body) if msg.html else (msg.text or "")[:30_000],
            ))

    issues.sort(key=lambda i: i.date)
    return _latest_per_newsletter(issues)


def _match(newsletters, from_header, subject):
    for n in newsletters:
        if n.matches(from_header, subject):
            return n
    return None


def _latest_per_newsletter(issues):
    """If several unprocessed issues exist for one newsletter, keep the newest."""
    latest = {}
    for issue in issues:
        latest[issue.newsletter_id] = issue
    return list(latest.values())
