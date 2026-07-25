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

# Senders that fan out into several distinct newsletters (same From address,
# teaser-only subjects). We dump list-identifying headers for these so their
# feeds can be told apart by header instead of subject.
AMBIGUOUS_SENDERS = ["dan@tldrnewsletter.com", "newsletters@coindesk.com"]
DIAG_HEADERS = ["list-id", "list-unsubscribe", "feedback-id", "x-campaign-id",
                "x-campaignid", "x-newsletter", "x-list", "to"]


def _header(msg, name: str) -> str:
    for k, v in (msg.headers or {}).items():
        if k.lower() == name:
            val = v[0] if isinstance(v, (list, tuple)) else v
            return (val or "").replace("\r", " ").replace("\n", " ").strip()
    return ""


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    address = os.environ.get("GMAIL_ADDRESS", "").strip()
    password = os.environ.get("GMAIL_APP_PASSWORD", "")

    if not address or not password:
        missing = [k for k in ("GMAIL_ADDRESS", "GMAIL_APP_PASSWORD")
                   if not os.environ.get(k, "").strip()]
        print("Setup problem: these are empty or not set -> " + ", ".join(missing))
        print("Set them as GitHub Actions secrets (or env vars when running locally).")
        sys.exit(1)

    # Gmail app passwords are 16 chars with NO spaces; Google shows them grouped
    # like 'abcd efgh ijkl mnop', so tolerate a value pasted with spaces.
    if " " in password:
        print("Note: GMAIL_APP_PASSWORD had spaces in it; using it with spaces removed.")
        password = password.replace(" ", "")

    since = (datetime.now(timezone.utc) - timedelta(days=10)).date()
    _, newsletters = load_config()
    matched = defaultdict(list)   # newsletter.id -> [subjects]
    senders = Counter()
    unmatched = []
    diag = defaultdict(list)      # ambiguous sender -> [(subject, {header: value})]

    try:
        mailbox = MailBox("imap.gmail.com").login(address, password)
    except Exception as e:
        print(f"IMAP login FAILED for {address}: {e}\n")
        print("Checklist:")
        print("  - GMAIL_APP_PASSWORD must be a 16-char Google *app password*,")
        print("    NOT your normal Gmail password.")
        print("  - Generate it at https://myaccount.google.com/apppasswords")
        print("    (2-Step Verification must be on first).")
        print("  - Make sure GMAIL_ADDRESS is the exact inbox address.")
        sys.exit(1)

    with mailbox:
        for msg in mailbox.fetch(AND(date_gte=since), mark_seen=False,
                                 headers_only=True, bulk=True):
            senders[msg.from_] += 1
            hit = next((n for n in newsletters if n.matches(msg.from_, msg.subject)), None)
            if hit:
                matched[hit.id].append(msg.subject)
            else:
                unmatched.append(f"{msg.from_}  |  {msg.subject}")

            from_l = (msg.from_ or "").lower()
            for amb in AMBIGUOUS_SENDERS:
                if amb in from_l:
                    diag[amb].append((msg.subject,
                                      {h: _header(msg, h) for h in DIAG_HEADERS}))

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

    print("\n== Header discriminators for shared senders ==")
    print("(used to tell apart newsletters that share one From address)")
    for amb in AMBIGUOUS_SENDERS:
        print(f"\n--- {amb} ({len(diag.get(amb, []))} emails) ---")
        for subject, headers in diag.get(amb, []):
            print(f"  SUBJECT: {(subject or '')[:70]}")
            for h in DIAG_HEADERS:
                val = headers.get(h, "")
                if val:
                    print(f"    {h}: {val[:110]}")


if __name__ == "__main__":
    main()
