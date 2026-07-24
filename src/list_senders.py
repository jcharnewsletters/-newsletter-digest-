"""Verify that config/newsletters.yml matches the real inbox.

    GMAIL_ADDRESS=... GMAIL_APP_PASSWORD=... python -m src.list_senders

Prints, for each configured newsletter, how many recent emails it matched and a
sample subject (0 matches almost always means a wrong sender/subject pattern).
Then lists any emails that matched no newsletter, so you can spot missing ones.
"""
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from imap_tools import MailBox, AND

from .config import load_config


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    address = os.environ["GMAIL_ADDRESS"]
    password = os.environ["GMAIL_APP_PASSWORD"]
    since = (datetime.now(timezone.utc) - timedelta(days=10)).date()

    _, newsletters = load_config()
    matched = defaultdict(list)   # newsletter.id -> [subjects]
    senders = Counter()
    unmatched = []

    with MailBox("imap.gmail.com").login(address, password) as mailbox:
        for msg in mailbox.fetch(AND(date_gte=since), mark_seen=False,
                                 headers_only=True, bulk=True):
            senders[msg.from_] += 1
            hit = next((n for n in newsletters if n.matches(msg.from_, msg.subject)), None)
            if hit:
                matched[hit.id].append(msg.subject)
            else:
                unmatched.append(f"{msg.from_}  |  {msg.subject}")

    print("== Per-newsletter match check (last 10 days) ==")
    for n in newsletters:
        subs = matched.get(n.id, [])
        flag = "" if subs else "   <-- 0 MATCHES, check patterns"
        sample = f'  e.g. "{subs[0][:70]}"' if subs else ""
        print(f"[{len(subs):2d}] {n.name}{flag}{sample}")

    print("\n== Emails matched by NO newsletter ==")
    for line in unmatched or ["(none)"]:
        print(line)

    print("\n== All senders seen (for reference) ==")
    for sender, count in senders.most_common():
        print(f"{count:3d}  {sender}")


if __name__ == "__main__":
    main()
