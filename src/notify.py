"""Send the alert email for a batch: digest inline + link to the website.

Sends from the dedicated Gmail account over SMTP using the same app password
as the IMAP fetch. Env vars: GMAIL_ADDRESS, GMAIL_APP_PASSWORD, ALERT_RECIPIENT,
SITE_URL (optional; falls back to a placeholder).
"""
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465

_EMOJI = {"stocks": "📈", "crypto": "🪙", "ai": "🤖"}


def send_alert(batch, category, date_str, digest, dry_run=False) -> None:
    subject = f"{_EMOJI.get(category, '📰')} {batch.label} digest — {date_str}"
    html = _render_html(batch, date_str, digest)

    if dry_run:
        print(f"[dry-run] would send email: {subject}")
        print(html[:2000])
        return

    sender = os.environ["GMAIL_ADDRESS"]
    password = os.environ["GMAIL_APP_PASSWORD"]
    recipient = os.environ["ALERT_RECIPIENT"]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient
    msg.attach(MIMEText(html, "html", "utf-8"))

    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
        server.login(sender, password)
        server.sendmail(sender, [recipient], msg.as_string())


def _render_html(batch, date_str, digest) -> str:
    site_url = os.environ.get("SITE_URL", "")
    parts = [f"<h2>{batch.label} — {date_str}</h2>"]
    if site_url:
        parts.append(f'<p><a href="{site_url}">Open the full digest site →</a></p>')

    if digest["top_stories"]:
        parts.append("<h3>⭐ Top stories across your newsletters</h3>")
        for story in digest["top_stories"]:
            parts.append(f"<h4>{story['title']}</h4><ul>")
            parts.extend(f"<li>{p}</li>" for p in story["points"])
            parts.append("</ul>")
            if story["unique_angles"]:
                parts.append("<ol>")
                parts.extend(
                    f"<li><b>{a['newsletter']}:</b> {a['point']}</li>"
                    for a in story["unique_angles"])
                parts.append("</ol>")
            parts.append(
                f"<p style='color:#6b7280;font-size:13px'>Covered by: "
                f"{', '.join(story['covered_by'])}</p>")

    for nl in digest["by_newsletter"]:
        if not nl["items"]:
            continue
        parts.append(f"<h3>{nl['newsletter']}</h3>")
        for i, item in enumerate(nl["items"], 1):
            parts.append(f"<h4>{i}. {item['title']}</h4><ul>")
            parts.extend(f"<li>{p}</li>" for p in item["points"])
            parts.append("</ul>")

    return "<html><body style='font-family:Georgia,serif;max-width:680px'>" \
           + "\n".join(parts) + "</body></html>"
