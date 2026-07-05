"""Convert newsletter HTML email bodies into clean plain text for the AI stage.

Newsletter emails are heavy with tracking pixels, sponsor blocks, and layout
tables; this strips the noise while keeping the readable text and the links.
"""
import re

from bs4 import BeautifulSoup

MAX_CHARS = 30_000  # keep prompts bounded; newsletters rarely exceed this

_FOOTER_MARKERS = [
    "unsubscribe", "manage your subscription", "update your preferences",
    "sent to you because", "view in browser", "email preferences",
]


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html or "", "html.parser")

    for tag in soup(["script", "style", "head", "title", "img"]):
        tag.decompose()

    # Keep link targets inline so the summarizer can preserve "read more" URLs.
    for a in soup.find_all("a"):
        href = a.get("href", "")
        text = a.get_text(" ", strip=True)
        if href.startswith("http") and text and len(text) > 2:
            a.replace_with(f"{text} <{href}>")

    text = soup.get_text("\n")
    lines = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        lower = line.lower()
        if any(m in lower for m in _FOOTER_MARKERS):
            break  # everything after the footer marker is boilerplate
        lines.append(line)

    cleaned = "\n".join(lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned[:MAX_CHARS]
