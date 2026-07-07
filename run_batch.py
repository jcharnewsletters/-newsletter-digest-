"""Run one batch end to end:  fetch → clean → summarize → synthesize → site → alert.

Examples:
  python -m src.run_batch --batch ai-am                       # live
  DIGEST_STUB_LLM=1 python -m src.run_batch --batch ai-am \
      --fixtures tests/fixtures --dry-run                     # no credentials
"""
import argparse
import json
import os
import sys

from .build_site import build
from .clean import clean
from .common import DIGESTS, load_config, load_state, now_et, save_state
from .fetch_email import fetch
from .notify import send_alert
from .summarize import summarize_all
from .synthesize import synthesize


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", required=True)
    ap.add_argument("--fixtures", help="directory of fixture emails (offline test)")
    ap.add_argument("--dry-run", action="store_true", help="print the alert instead of sending")
    args = ap.parse_args()

    cfg = load_config()
    if args.batch not in cfg["batches"]:
        sys.exit(f"Unknown batch '{args.batch}'. Options: {', '.join(cfg['batches'])}")
    label = cfg["batches"][args.batch]["label"]
    date = now_et().strftime("%Y-%m-%d")

    print(f"[1/5] Fetching issues for {label}…")
    issues = fetch(cfg, args.batch, args.fixtures)
    expected = [n["name"] for n in cfg["newsletters"] if n["batch"] == args.batch]
    got = [i["newsletter"] for i in issues]
    for name in expected:
        if name not in got:
            print(f"      · {name}: no issue today (weekly, or not arrived) — skipped")
    if not issues:
        print("Nothing to digest today; exiting cleanly.")
        return
    print(f"      {len(issues)} issue(s): {', '.join(got)}")

    print("[2/5] Cleaning HTML → text…")
    issues = [clean(i) for i in issues]

    print(f"[3/5] Summarizing with {len(issues)} parallel sub-agents…")
    summaries = summarize_all(issues)

    print("[4/5] Synthesizing (merging overlap)…")
    digest_md = synthesize(label, summaries)

    DIGESTS.mkdir(parents=True, exist_ok=True)
    out = DIGESTS / f"{date}-{args.batch}.json"
    out.write_text(json.dumps({
        "date": date, "batch": args.batch, "label": label,
        "count": len(issues), "newsletters": got, "digest": digest_md,
    }, indent=2), encoding="utf-8")
    build()
    print(f"      Saved {out.name} and rebuilt docs/ (open docs/index.html)")

    print("[5/5] Sending alert email…")
    site_url = os.environ.get("SITE_URL", "")
    page_url = f"{site_url.rstrip('/')}/{date}-{args.batch}.html" if site_url else ""
    send_alert(label, date, digest_md, len(issues), page_url, dry_run=args.dry_run)

    state = load_state()
    state["last_sent"][args.batch] = date
    save_state(state)
    print("Done. ✅")


if __name__ == "__main__":
    main()
