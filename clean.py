"""Turn a newsletter email (HTML soup + tracking junk) into clean text."""
import re

from bs4 import BeautifulSoup

MAX_CHARS = 16000  # plenty for a summary; keeps token cost predictable

JUNK_LINE = re.compile(
    r"(view (this|in) browser|unsubscribe|manage (your )?preferences|"
    r"update your profile|forwarded this email|sent to you because|"
    r"privacy policy|advertise with us|copyright ©|\bsponsored?\b.{0,40}$)",
    re.IGNORECASE,
)


def clean(issue: dict) -> dict:
    html = issue.get("html") or ""
    text = issue.get("plain") or ""
    if html:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "head", "img", "svg"]):
            tag.decompose()
        text = soup.get_text(separator="\n")

    lines = []
    for line in text.splitlines():
        line = line.strip()
        if not line or JUNK_LINE.search(line):
            continue
        if re.fullmatch(r"[|•\-_=~*\s]+", line):  # decorative rules
            continue
        lines.append(line)

    # collapse runs of duplicate lines (common in table-based emails)
    deduped = [l for i, l in enumerate(lines) if i == 0 or l != lines[i - 1]]
    body = "\n".join(deduped)[:MAX_CHARS]
    return {**issue, "text": body}
