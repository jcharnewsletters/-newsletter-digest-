"""Regenerate the static website (docs/) from stored batch digests.

The site is rebuilt in full from data/summaries/ every run, so history is
never lost and template changes apply retroactively.
"""
import json
import shutil

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .config import SITE_DIR, SUMMARIES_DIR, TEMPLATES_DIR

BATCH_ORDER = ["stocks-am", "crypto-am", "ai-am", "crypto-pm", "ai-pm"]


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

    days = sorted([d.name for d in SUMMARIES_DIR.iterdir() if d.is_dir()], reverse=True) \
        if SUMMARIES_DIR.exists() else []

    SITE_DIR.mkdir(parents=True, exist_ok=True)
    (SITE_DIR / ".nojekyll").write_text("", encoding="utf-8")
    shutil.copyfile(TEMPLATES_DIR / "style.css", SITE_DIR / "style.css")
    archive_dir = SITE_DIR / "archive"
    archive_dir.mkdir(exist_ok=True)

    for i, day in enumerate(days):
        batches = _load_day(day)
        # Archive pages live one directory below docs/, hence root="../".
        html = day_template.render(
            date=day, batches=batches, days=days, is_latest=(i == 0), root="../")
        (archive_dir / f"{day}.html").write_text(html, encoding="utf-8")
        if i == 0:
            html_index = day_template.render(
                date=day, batches=batches, days=days, is_latest=True, root="")
            (SITE_DIR / "index.html").write_text(html_index, encoding="utf-8")

    if not days:
        html = day_template.render(date=None, batches=[], days=[], is_latest=True, root="")
        (SITE_DIR / "index.html").write_text(html, encoding="utf-8")


def _load_day(day: str) -> list:
    day_dir = SUMMARIES_DIR / day
    records = []
    for f in day_dir.glob("*.json"):
        records.append(json.loads(f.read_text(encoding="utf-8")))
    records.sort(key=lambda r: BATCH_ORDER.index(r["batch"]) if r["batch"] in BATCH_ORDER else 99)
    return records
