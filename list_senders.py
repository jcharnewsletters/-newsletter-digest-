"""List recent senders in the inbox and show which newsletters they match.

Usage (after setting GMAIL_ADDRESS / GMAIL_APP_PASSWORD):
    python -m src.list_senders
"""
import email
import email.policy
import imaplib
import os
from datetime import timedelta

from .common import load_config, now_et
from .fetch_email import IMAP_HOST, _matches


def main() -> None:
    cfg = load_config()
    address = os.environ["GMAIL_ADDRESS"]
    password = os.environ["GMAIL_APP_PASSWORD"].replace(" ", "")
    since = (now_et() - timedelta(days=7)).strftime("%d-%b-%Y")

    matched, unmatched = {}, []
    with imaplib.IMAP4_SSL(IMAP_HOST) as imap:
        imap.login(address, password)
        imap.select("INBOX", readonly=True)
        _, data = imap.search(None, f'(SINCE "{since}")')
        for mid in data[0].split():
            _, msg_data = imap.fetch(mid, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT)])")
            msg = email.message_from_bytes(msg_data[0][1], policy=email.policy.default)
            frm, subj = msg.get("From", ""), msg.get("Subject", "")
            hit = next((n["name"] for n in cfg["newsletters"] if _matches(n, frm, subj)), None)
            if hit:
                matched.setdefault(hit, frm)
            else:
                unmatched.append(f"{frm}  |  {subj[:60]}")

    print("MATCHED:")
    for name, frm in sorted(matched.items()):
        print(f"  ✓ {name:<24} ← {frm}")
    print("\nNOT matched (add a sender pattern to config/newsletters.yml if these are newsletters):")
    for line in sorted(set(unmatched)):
        print(f"  ✗ {line}")
    missing = [n["name"] for n in cfg["newsletters"] if n["name"] not in matched]
    if missing:
        print(f"\nNo mail seen in 7 days from: {', '.join(missing)}")


if __name__ == "__main__":
    main()
