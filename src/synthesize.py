"""Stage 2: synthesis agent.

Takes all Stage-1 summaries in a batch and removes cross-newsletter overlap:
stories covered by more than one newsletter are merged into a single "top
stories" entry; everything unique stays under its newsletter's own heading.
"""
import json
import os

import anthropic

from .config import SYNTH_MODEL

DIGEST_SCHEMA = {
    "type": "object",
    "properties": {
        "top_stories": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "points": {"type": "array", "items": {"type": "string"}},
                    "covered_by": {"type": "array", "items": {"type": "string"}},
                    "unique_angles": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "newsletter": {"type": "string"},
                                "point": {"type": "string"},
                            },
                            "required": ["newsletter", "point"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["title", "points", "covered_by", "unique_angles"],
                "additionalProperties": False,
            },
        },
        "by_newsletter": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "newsletter": {"type": "string"},
                    "items": {
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
                    },
                },
                "required": ["newsletter", "items"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["top_stories", "by_newsletter"],
    "additionalProperties": False,
}

SYSTEM_PROMPT = """You merge summaries of several newsletters from the same day into one \
non-redundant digest for a busy reader. Rules:
- A story covered by TWO OR MORE newsletters goes in top_stories exactly once: merged points \
(no repetition), covered_by listing every newsletter that ran it, and unique_angles capturing \
anything only one newsletter added.
- A story covered by only ONE newsletter stays under that newsletter in by_newsletter. \
Never duplicate a top story there.
- Keep every point scannable: concrete facts and numbers first, one sentence each.
- If a technical term appears, keep (or add) a plain-English definition in parentheses at its \
first use — detailed enough for a complete newcomer.
- Include every newsletter that had content in by_newsletter, even if all its big stories were \
promoted to top_stories (then list its remaining smaller items, or an empty items list)."""


def synthesize_batch(batch_label: str, summarized: list) -> dict:
    """summarized: output of summarize_issues(). Returns the digest dict."""
    if not summarized:
        return {"top_stories": [], "by_newsletter": []}
    if os.environ.get("DIGEST_STUB_LLM"):
        return _stub_digest(summarized)

    payload = [
        {"newsletter": s["issue"].newsletter_name,
         "subject": s["issue"].subject,
         "summary": s["summary"]}
        for s in summarized
    ]
    client = anthropic.Anthropic()
    response = client.messages.create(
        model=SYNTH_MODEL,
        max_tokens=16000,
        system=SYSTEM_PROMPT,
        output_config={"format": {"type": "json_schema", "schema": DIGEST_SCHEMA}},
        messages=[{
            "role": "user",
            "content": (
                f"Batch: {batch_label}\n\n"
                "Per-newsletter summaries (JSON):\n"
                + json.dumps(payload, indent=2)
            ),
        }],
    )
    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text)


def _stub_digest(summarized) -> dict:
    names = [s["issue"].newsletter_name for s in summarized]
    top = []
    if len(summarized) >= 2:
        top = [{
            "title": "[stub] Shared story across newsletters",
            "points": ["[stub] merged point"],
            "covered_by": names[:2],
            "unique_angles": [{"newsletter": names[0], "point": "[stub] unique angle"}],
        }]
    return {
        "top_stories": top,
        "by_newsletter": [
            {"newsletter": s["issue"].newsletter_name,
             "items": [{"title": sec["title"], "points": sec["points"]}
                       for sec in s["summary"]["sections"]]}
            for s in summarized
        ],
    }
