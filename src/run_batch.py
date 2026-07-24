"""Entry point: run one batch end-to-end.

    python -m src.run_batch --batch ai-am
    python -m src.run_batch --batch ai-am --fixtures tests/fixtures --dry-run

Steps: fetch new emails -> summarize each issue (parallel sub-agents) ->
synthesize/dedupe the batch -> save digest + rebuild site -> send alert email
-> persist state.
"""
import argparse
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from . import state as state_mod
from .build_site import build_site, save_batch_digest
from .config import TIMEZONE, load_config
from .notify import send_alert
from .summarize import summarize_issues
from .synthesize import synthesize_batch


def main() -> int:
    # Windows consoles default to cp1252, which can't print emoji in subjects.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Run one newsletter digest batch")
    parser.add_argument("--batch", required=True, help="batch id, e.g. ai-am")
    parser.add_argument("--dry-run", action="store_true",
                        help="print the alert email instead of sending; don't persist state")
    parser.add_argument("--fixtures", metavar="DIR",
                        help="read issues from local HTML files instead of Gmail")
    parser.add_argument("--force", action="store_true",
                        help="run even if this batch already ran today")
    args = parser.parse_args()

    batches, _ = load_config()
    if args.batch not in batches:
        print(f"Unknown batch '{args.batch}'. Valid: {', '.join(batches)}")
        return 2
    batch = batches[args.batch]
    today = datetime.now(ZoneInfo(TIMEZONE)).strftime("%Y-%m-%d")

    state = state_mod.load_state()
    if state_mod.batch_ran_on(state, batch.id, today) and not (args.force or args.dry_run):
        print(f"Batch {batch.id} already ran on {today}; skipping (use --force to override).")
        return 0

    # 1. Fetch
    if args.fixtures:
        issues = _load_fixtures(Path(args.fixtures), batch)
    else:
        from .fetch_email import fetch_issues
        issues = fetch_issues(batch.newsletters, state)
    print(f"Fetched {len(issues)} new issue(s) for batch {batch.id}.")

    if not issues:
        print("Nothing new (weekend / weekly gap). No site update, no alert.")
        if not args.dry_run:
            state_mod.mark_batch_run(state, batch.id, today)
            state_mod.save_state(state)
        return 0

    # 2. Summarizer sub-agents (parallel, one per issue)
    summarized = summarize_issues(issues)
    print(f"Summarized {len(summarized)} issue(s).")

    # 3. Cross-newsletter synthesis / dedup
    digest = synthesize_batch(batch.label, summarized)
    print(f"Synthesized digest: {len(digest['top_stories'])} top stories, "
          f"{len(digest['by_newsletter'])} newsletter sections.")

    # 4. Persist digest + rebuild site (skipped in dry-run so no committed
    #    files are mutated; the email preview below is enough to eyeball output)
    if not args.dry_run:
        save_batch_digest(today, batch, digest, summarized)
        build_site()
        print("Site rebuilt under docs/.")

    # 5. Alert email
    category = batch.newsletters[0].category if batch.newsletters else "ai"
    send_alert(batch, category, today, digest, dry_run=args.dry_run)
    if not args.dry_run:
        print("Alert email sent.")

    # 6. State
    if not args.dry_run:
        for s in summarized:
            state_mod.mark_processed(state, s["issue"].message_id)
        state_mod.mark_batch_run(state, batch.id, today)
        state_mod.save_state(state)
    return 0


def _load_fixtures(fixtures_dir: Path, batch):
    """Fixture files are named '<newsletter_id>__<anything>.html'."""
    from .clean import html_to_text
    from .fetch_email import Issue

    by_id = {n.id: n for n in batch.newsletters}
    issues = []
    for f in sorted(fixtures_dir.glob("*.html")):
        newsletter_id = f.name.split("__")[0]
        if newsletter_id not in by_id:
            continue
        n = by_id[newsletter_id]
        issues.append(Issue(
            newsletter_id=n.id,
            newsletter_name=n.name,
            message_id=f"fixture-{f.name}",
            subject=f.stem.split("__", 1)[-1].replace("-", " "),
            date=datetime.now(ZoneInfo(TIMEZONE)).isoformat(),
            text=html_to_text(f.read_text(encoding="utf-8")),
        ))
    return issues


if __name__ == "__main__":
    sys.exit(main())
