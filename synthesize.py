"""Stage 2: the synthesis agent (Claude Sonnet — the editor-in-chief).

Takes every sub-agent summary in the batch and produces ONE digest with the
overlap merged away: each story appears exactly once, tagged with which
newsletters covered it.
"""
from .common import stub_mode

MODEL = "claude-sonnet-4-6"

SYSTEM = """You are the editor-in-chief of a personal newsletter digest.
You receive per-newsletter summaries that overlap heavily. Produce ONE
non-redundant digest in markdown:

- Start with a numbered list ("1.", "2.", ...) of distinct stories, most
  important first. Each item: a bold one-line headline, then 1–3 short "-"
  sub-bullets with the key facts and numbers.
- If several newsletters covered the same story, MERGE them into a single
  item and end it with: _(covered by: X, Y, Z)_. Never repeat a story.
- If a necessary technical term appears, define it in plain English in
  parentheses at first use — in great detail but briefly, for a reader with
  zero background.
- End with a section "**⏭ Skipped as redundant:**" — one line listing what
  was merged, so the reader trusts nothing was lost.
- No preamble, no sign-off. Scannable above all."""


def synthesize(batch_label: str, summaries: list[dict]) -> str:
    if stub_mode():
        names = ", ".join(s["newsletter"] for s in summaries)
        return (
            "1. **Stubbed top story — the pipeline works end to end.**\n"
            "   - This digest was produced with DIGEST_STUB_LLM=1 (a 'stub' is a "
            "stand-in used for testing, so no API calls were made).\n"
            f"   - _(covered by: {names})_\n"
            "2. **Second stubbed story with a number: 42%.**\n"
            "   - Everything downstream — site build and email — is real.\n\n"
            "**⏭ Skipped as redundant:** nothing; stub mode.\n"
        )
    import anthropic
    client = anthropic.Anthropic()
    blob = "\n\n---\n\n".join(
        f"### {s['newsletter']} — {s['subject']}\n{s['summary']}" for s in summaries
    )
    resp = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        system=SYSTEM,
        messages=[{"role": "user", "content": f"Batch: {batch_label}\n\n{blob}"}],
    )
    return "".join(b.text for b in resp.content if b.type == "text")
