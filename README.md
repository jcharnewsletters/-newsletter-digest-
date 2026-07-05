# Newsletter Digest Agent

Automated pipeline that reads ~20 AI / crypto / stock-market newsletters from a
dedicated Gmail inbox, summarizes each issue with parallel Claude sub-agents,
merges overlapping stories into a single non-redundant digest, publishes a
website (GitHub Pages), and emails an alert for each batch on a fixed
Eastern-Time schedule.

```
Gmail inbox ──IMAP──▶ fetch ─▶ clean ─▶ summarizer sub-agents (parallel, Haiku)
                                              │
                                              ▼
                              synthesis agent (Sonnet — dedupes overlap)
                                              │
                          ┌───────────────────┴───────────────────┐
                          ▼                                       ▼
              static site → docs/ (GitHub Pages)        alert email (SMTP)
```

## Daily schedule (Eastern Time)

| Batch | Alert by | Newsletters |
|---|---|---|
| `stocks-am` | 9:15 AM | Opening Bell, Yahoo Finance, Wall Street Breakfast, Bloomberg, CNBC, Investopedia |
| `crypto-am` | 9:30 AM | CMC Spotlight, CMC Market Pulse, CoinDesk Daybook, TLDR Crypto |
| `ai-am` | 10:00 AM | The Neuron, The Rundown AI, Superhuman, TLDR AI, Ben's Bites |
| `crypto-pm` | 7:00 PM | Decrypt Daily Hash, Bitcoin Magazine |
| `ai-pm` | 10:00 PM | Everyday AI, Lenny's Newsletter, The Batch, AI Daily Brief |

Scheduling runs on GitHub Actions (`.github/workflows/digest.yml`) with two
cron entries per batch and a guard step so daylight-saving changes never shift
or double-fire a batch.

## Setup

See [SETUP.md](SETUP.md) — one-time, ~45 minutes.

## Local testing (no credentials needed)

```
pip install -r requirements.txt
set DIGEST_STUB_LLM=1        # PowerShell: $env:DIGEST_STUB_LLM="1"
python -m src.run_batch --batch ai-am --fixtures tests/fixtures --dry-run
```

This runs the entire pipeline against sample emails with a stubbed AI stage,
rebuilds `docs/`, and prints the alert email instead of sending it. Open
`docs/index.html` in a browser to see the site.

## Layout

| Path | Purpose |
|---|---|
| `config/newsletters.yml` | newsletter registry: senders, batches, cadence |
| `src/run_batch.py` | entry point — one batch end-to-end |
| `src/fetch_email.py` / `src/clean.py` | IMAP fetch + HTML-to-text cleanup |
| `src/summarize.py` / `src/synthesize.py` | the two AI stages |
| `src/build_site.py` + `templates/` | static site generator |
| `src/notify.py` | alert email via Gmail SMTP |
| `src/list_senders.py` | helper to verify sender patterns after subscribing |
| `data/` | state + stored digests (committed by the workflow) |
| `docs/` | the generated website (served by GitHub Pages) |
