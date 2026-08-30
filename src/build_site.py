"""Regenerate the static website (docs/) from stored batch digests.

The site is rebuilt in full from data/summaries/ every run, so history is
never lost and template changes apply retroactively.
"""
import json
import shutil

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .config import SITE_DIR, SUMMARIES_DIR, TEMPLATES_DIR

BATCH_ORDER = ["stocks-am", "crypto-am", "ai-am", "tech-am", "crypto-pm", "ai-pm"]

# How many of the most recent digest days the site shows (one week).
# Older days stay in data/summaries/ — only the published pages are trimmed —
# so raising this number brings the full history straight back.
ARCHIVE_DAYS = 7


def save_batch_digest(date_str, batch, digest, summarized) -> None:
    day_dir = SUMMARIES_DIR / date_str
    day_dir.mkdir(parents=True, exist_ok=True)
    category = batch.newsletters[0].category if batch.newsletters else "ai"
    record = {
        "batch": batch.id,
        "label": batch.label,
        "category": category,
        "date": date_str,
        "digest": digest,
        "issues": [
            {"newsletter": s["issue"].newsletter_name,
             "subject": s["issue"].subject,
             "date": s["issue"].date,
             "summary": s["summary"]}
            for s in summarized
        ],
    }
    (day_dir / f"{batch.id}.json").write_text(
        json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")


def build_site() -> None:
    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=select_autoescape(["html"]),
    )
    day_template = env.get_template("day.html.j2")

    all_days = sorted([d.name for d in SUMMARIES_DIR.iterdir() if d.is_dir()], reverse=True) \
        if SUMMARIES_DIR.exists() else []
    days = all_days[:ARCHIVE_DAYS]

    SITE_DIR.mkdir(parents=True, exist_ok=True)
    (SITE_DIR / ".nojekyll").write_text("", encoding="utf-8")
    shutil.copyfile(TEMPLATES_DIR / "style.css", SITE_DIR / "style.css")
    archive_dir = SITE_DIR / "archive"
    archive_dir.mkdir(exist_ok=True)

    for i, day in enumerate(days):
        batches = _load_day(day)
        glance = _glance(batches)
        # Archive pages live one directory below docs/, hence root="../".
        html = day_template.render(
            date=day, batches=batches, glance=glance,
            days=days, is_latest=(i == 0), root="../")
        (archive_dir / f"{day}.html").write_text(html, encoding="utf-8")
        if i == 0:
            html_index = day_template.render(
                date=day, batches=batches, glance=glance,
                days=days, is_latest=True, root="")
            (SITE_DIR / "index.html").write_text(html_index, encoding="utf-8")

    if not days:
        html = day_template.render(
            date=None, batches=[], glance=[], days=[], is_latest=True, root="")
        (SITE_DIR / "index.html").write_text(html, encoding="utf-8")

    # Drop published pages for days that rolled out of the window, so old
    # digests aren't left orphaned (unlinked but still reachable) in docs/.
    keep = {f"{d}.html" for d in days}
    for stale in archive_dir.glob("*.html"):
        if stale.name not in keep:
            stale.unlink()


def _glance(batches: list) -> list:
    """One headline per batch for the 'Top things to know today' banner:
    the first top story if there is one, else the first per-newsletter item."""
    items = []
    for r in batches:
        digest = r["digest"]
        headline = None
        if digest.get("top_stories"):
            headline = digest["top_stories"][0]["title"]
        else:
            for nl in digest.get("by_newsletter", []):
                if nl.get("items"):
                    headline = nl["items"][0]["title"]
                    break
        if headline:
            items.append({"label": r["label"], "category": r["category"],
                          "anchor": r["batch"], "headline": headline})
    return items


def _load_day(day: str) -> list:
    day_dir = SUMMARIES_DIR / day
    records = []
    for f in day_dir.glob("*.json"):
        records.append(json.loads(f.read_text(encoding="utf-8")))
    records.sort(key=lambda r: BATCH_ORDER.index(r["batch"]) if r["batch"] in BATCH_ORDER else 99)
    return records
