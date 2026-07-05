"""Stage 1: summarizer sub-agents.

Each newsletter issue gets its own Claude API call (one independent AI worker
per issue), run in parallel. Structured outputs guarantee valid JSON.

Set DIGEST_STUB_LLM=1 to skip the API and produce deterministic fake summaries
— used for offline pipeline testing before credentials exist.
"""
import json
import os
from concurrent.futures import ThreadPoolExecutor

import anthropic

from .config import SUMMARIZE_MODEL

ISSUE_SCHEMA = {
    "type": "object",
    "properties": {
        "headlines": {
            "type": "array", "items": {"type": "string"},
            "description": "3-5 scannable bullet points covering the issue's biggest stories",
        },
        "sections": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "points": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["title", "points"],
                "additionalProperties": False,
            },
            "description": "Numbered deep-dive sections for stories that deserve more than a bullet",
        },
        "links": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "label": {"type": "string"},
                    "url": {"type": "string"},
                },
                "required": ["label", "url"],
                "additionalProperties": False,
            },
            "description": "Up to 5 'read more' links preserved from the issue",
        },
    },
    "required": ["headlines", "sections", "links"],
    "additionalProperties": False,
}

SYSTEM_PROMPT = """You summarize a single newsletter issue for a busy professional \
who has no time to read the original. Rules:
- Headlines: 3-5 bullets, each one self-contained sentence stating what happened and why it matters.
- Sections: for the 2-4 most substantial stories, a short title plus 2-4 numbered points each.
- Every point must be scannable: lead with the concrete fact or number, no filler, no hype.
- If you must use a technical term (e.g. "staking", "context window", "basis point"), define it \
in plain English in parentheses immediately where it first appears, in enough detail that a \
newcomer understands it without looking anything up.
- Preserve up to 5 of the most useful source links from the text (they appear as <https://...>).
- Skip sponsor content, job boards, memes, and self-promotion entirely."""


def summarize_issues(issues) -> list:
    """Return [{'issue': Issue, 'summary': dict}, ...] preserving input order."""
    if not issues:
        return []
    if os.environ.get("DIGEST_STUB_LLM"):
        return [{"issue": i, "summary": _stub_summary(i)} for i in issues]

    client = anthropic.Anthropic()
    with ThreadPoolExecutor(max_workers=min(6, len(issues))) as pool:
        summaries = list(pool.map(lambda i: _summarize_one(client, i), issues))
    return [{"issue": i, "summary": s} for i, s in zip(issues, summaries)]


def _summarize_one(client, issue) -> dict:
    response = client.messages.create(
        model=SUMMARIZE_MODEL,
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        output_config={"format": {"type": "json_schema", "schema": ISSUE_SCHEMA}},
        messages=[{
            "role": "user",
            "content": (
                f"Newsletter: {issue.newsletter_name}\n"
                f"Subject: {issue.subject}\n"
                f"Date: {issue.date}\n\n"
                f"Full text:\n{issue.text}"
            ),
        }],
    )
    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text)


def _stub_summary(issue) -> dict:
    first_lines = [l for l in issue.text.splitlines() if len(l) > 30][:4]
    return {
        "headlines": [f"[stub] {l[:120]}" for l in first_lines] or [f"[stub] {issue.subject}"],
        "sections": [{"title": f"[stub] Deep dive: {issue.subject[:60]}",
                      "points": ["[stub] point 1", "[stub] point 2"]}],
        "links": [],
    }
