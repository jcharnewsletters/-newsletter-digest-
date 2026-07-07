"""Send the alert email with the generated digest via Gmail SMTP.

The most common reasons this stage silently fails (worth knowing since it is
exactly the stage that broke):
  1. GMAIL_APP_PASSWORD stored WITH spaces — Google displays it as
     "abcd efgh ijkl mnop"; it must be saved as 16 characters, no spaces.
     (This code strips spaces defensively either way.)
  2. Using the account's real password instead of an app password.
  3. Port 587 without STARTTLS — we use SSL on 465, which just works.
  4. Exceptions swallowed by a bare try/except — here any failure raises
     loudly so the GitHub Actions run goes RED instead of pretending.
"""
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from .build_site import md_to_html

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465  # SSL


def send_alert(label: str, date: str, digest_md: str, count: int,
               site_url: str = "", dry_run: bool = False) -> None:
    sender = os.environ.get("GMAIL_ADDRESS", "digest@example.com")
    password = os.environ.get("GMAIL_APP_PASSWORD", "").replace(" ", "")
    recipient = os.environ.get("ALERT_RECIPIENT", sender)

    subject = f"📬 {label} digest — {date} ({count} newsletters)"
    link = f"<p><a href='{site_url}'>Read on the site →</a></p>" if site_url else ""
    html_body = (f"<div style='font-family:system-ui,sans-serif;max-width:680px'>"
                 f"<h2 style='margin:0 0 12px'>{label} — {date}</h2>"
                 f"{md_to_html(digest_md)}{link}</div>")

    msg = MIMEMultipart("alternative")
    msg["Subject"], msg["From"], msg["To"] = subject, sender, recipient
    msg.attach(MIMEText(digest_md, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    if dry_run:
        print("=" * 60)
        print(f"[dry-run] Would send: {subject}")
        print(f"[dry-run] To: {recipient}")
        print("=" * 60)
        print(digest_md)
        return

    if not password:
        raise SystemExit("GMAIL_APP_PASSWORD is empty — cannot send alert.")
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=30) as smtp:
        smtp.login(sender, password)
        smtp.sendmail(sender, [recipient], msg.as_string())
    print(f"Alert sent to {recipient}: {subject}")
