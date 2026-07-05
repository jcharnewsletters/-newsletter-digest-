"""Helper: print the actual From addresses in the inbox so config/newsletters.yml
sender patterns can be verified after subscribing.

    GMAIL_ADDRESS=... GMAIL_APP_PASSWORD=... python -m src.list_senders
"""
import os
from collections import Counter
from datetime import datetime, timedelta, timezone

from imap_tools import MailBox, AND

from .config import load_config


def main() -> None:
    address = os.environ["GMAIL_ADDRESS"]
    password = os.environ["GMAIL_APP_PASSWORD"]
    since = (datetime.now(timezone.utc) - timedelta(days=10)).date()

    _, newsletters = load_config()
    senders = Counter()
    unmatched = []
    with MailBox("imap.gmail.com").login(address, password) as mailbox:
        for msg in mailbox.fetch(AND(date_gte=since), mark_seen=False, headers_only=True, bulk=True):
            senders[msg.from_] += 1
            if not any(n.matches(msg.from_, msg.subject) for n in newsletters):
                unmatched.append(f"{msg.from_}  |  {msg.subject}")

    print("== All senders (last 10 days) ==")
    for sender, count in senders.most_common():
        print(f"{count:3d}  {sender}")

    print("\n== Emails NOT matched by config/newsletters.yml ==")
    for line in unmatched:
        print(line)
    if not unmatched:
        print("(none — every email matched a configured newsletter)")


if __name__ == "__main__":
    main()
