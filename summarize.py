"""Stage 1 of the AI pipeline: one sub-agent per newsletter, run in parallel.

Each sub-agent (Claude Haiku — small/fast/cheap) turns one issue into a
scannable bullet summary. Plain-English definitions are required the moment
any technical term appears.
"""
from concurrent.futures import ThreadPoolExecutor

from .common import stub_mode

MODEL = "claude-haiku-4-5-20251001"

SYSTEM = """You summarize one issue of a finance/crypto/AI newsletter.

Rules:
- Output ONLY markdown bullet points (use "-"), grouped under short bold
  topic labels when helpful. No intro, no outro.
- 4–8 bullets covering every substantive story; each bullet is one or two
  short sentences, easy to scan.
- If a necessary technical term appears (e.g. "basis point", "staking",
  "context window"), define it in plain English in parentheses the moment
  it is first used — assume a smart reader with zero domain background.
- Skip ads, sponsor blocks, referral asks, and self-promotion entirely.
- Keep concrete numbers (prices, %, dates) — they are the point."""


def _summarize_one(client, issue: dict) -> dict:
    if stub_mode():
        summary = (
            f"- **Top story:** stubbed summary of *{issue['subject']}* — the pipeline "
            f"ran without calling the API (a 'stub' is a stand-in used for testing).\n"
            f"- Second bullet with a concrete number: 42%.\n"
            f"- Third bullet defining a term (plain English: a simple explanation)."
        )
    else:
        resp = client.messages.create(
            model=MODEL,
            max_tokens=800,
            system=SYSTEM,
            messages=[{
                "role": "user",
                "content": f"Newsletter: {issue['newsletter']}\n"
                           f"Subject: {issue['subject']}\n\n{issue['text']}",
            }],
        )
        summary = "".join(b.text for b in resp.content if b.type == "text")
    return {"newsletter": issue["newsletter"], "subject": issue["subject"], "summary": summary}


def summarize_all(issues: list[dict]) -> list[dict]:
    client = None
    if not stub_mode():
        import anthropic
        client = anthropic.Anthropic()  # uses ANTHROPIC_API_KEY
    with ThreadPoolExecutor(max_workers=min(6, max(1, len(issues)))) as pool:
        return list(pool.map(lambda i: _summarize_one(client, i), issues))
