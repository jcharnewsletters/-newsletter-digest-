"""Rebuild docs/ (the GitHub Pages site) from every stored digest."""
import html
import json
import re

from .common import DIGESTS, DOCS

CSS = """
body{font-family:system-ui,-apple-system,'Segoe UI',sans-serif;max-width:760px;
margin:0 auto;padding:24px 20px 60px;color:#16233A;background:#F5F7FB;line-height:1.55}
h1{letter-spacing:-.02em}
.card{background:#fff;border:1px solid #DDE3EE;border-radius:14px;padding:22px 26px;margin:16px 0}
.meta{color:#61708A;font-size:13px;margin-bottom:8px}
a{color:#2E5BFF;text-decoration:none} a:hover{text-decoration:underline}
li{margin:6px 0} em{color:#61708A}
"""


def md_to_html(md: str) -> str:
    """Small converter for the subset of markdown the digests use."""
    out, in_ol, in_ul = [], False, False

    def close():
        nonlocal in_ol, in_ul
        if in_ol: out.append("</ol>"); in_ol = False
        if in_ul: out.append("</ul>"); in_ul = False

    def inline(s: str) -> str:
        s = html.escape(s)
        s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
        s = re.sub(r"_(.+?)_", r"<em>\1</em>", s)
        return s

    for line in md.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("###"): close(); out.append(f"<h3>{inline(s[3:].strip())}</h3>")
        elif s.startswith("##"): close(); out.append(f"<h2>{inline(s[2:].strip())}</h2>")
        elif s.startswith("#"):  close(); out.append(f"<h1>{inline(s[1:].strip())}</h1>")
        elif re.match(r"^\d+\.\s", s):
            if in_ul: out.append("</ul>"); in_ul = False
            if not in_ol: out.append("<ol>"); in_ol = True
            out.append("<li>" + inline(re.sub(r"^\d+\.\s", "", s)) + "</li>")
        elif s.startswith("- "):
            if not in_ol and not in_ul: out.append("<ul>"); in_ul = True
            tag = f"<ul style='margin:4px 0'><li>{inline(s[2:])}</li></ul>" if in_ol else f"<li>{inline(s[2:])}</li>"
            # nest sub-bullets inside the current <ol> item simply:
            out.append(tag if in_ol else f"<li>{inline(s[2:])}</li>")
        else:
            close(); out.append(f"<p>{inline(s)}</p>")
    close()
    return "\n".join(out)


def page(title: str, body: str) -> str:
    return (f"<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>"
            f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{html.escape(title)}</title><style>{CSS}</style></head>"
            f"<body>{body}</body></html>")


def build() -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    digests = sorted(DIGESTS.glob("*.json"), reverse=True)
    cards = []
    for path in digests:
        d = json.loads(path.read_text(encoding="utf-8"))
        slug = path.stem
        detail = (f"<p><a href='index.html'>← all digests</a></p>"
                  f"<div class='card'><div class='meta'>{d['date']} · {d['label']} · "
                  f"{d['count']} newsletters</div>{md_to_html(d['digest'])}</div>")
        (DOCS / f"{slug}.html").write_text(page(f"{d['label']} — {d['date']}", detail), encoding="utf-8")
        cards.append(f"<div class='card'><div class='meta'>{d['date']}</div>"
                     f"<b><a href='{slug}.html'>{d['label']}</a></b> — {d['count']} newsletters</div>")
    index = "<h1>📬 Newsletter Digest</h1><p class='meta'>Auto-generated. Newest first.</p>" + "".join(cards or ["<p>No digests yet.</p>"])
    (DOCS / "index.html").write_text(page("Newsletter Digest", index), encoding="utf-8")
