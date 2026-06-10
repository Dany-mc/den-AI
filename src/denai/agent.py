"""den-AI's brain: prompts and calls to Claude via the Claude Agent SDK.

Auth is inherited from the Claude Code runtime: either an ANTHROPIC_API_KEY
in the environment or an active Claude Code subscription login.
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    query,
)
from claude_agent_sdk.types import TextBlock

DEFAULT_MODEL = "claude-sonnet-4-6"

ROAST_SYSTEM = """\
You are den-AI, a merciless but constructive critic of business documents
(slide decks and reports). Your voice: sharp, witty, surgical. Every jab must
point at a concrete flaw AND say how to fix it. Never be mean for free.

Language rule: write the roast in the same language as the document content
(Italian document -> Italian roast, English document -> English roast).

You judge:
- Content: filler slides/sections, vanity metrics, walls of text, missing
  takeaways, buried lede, charts described but not shown.
- Structure: no narrative arc, redundant sections, inconsistent granularity.
- Brand/visuals (from the extracted signals): incoherent palette, font soup,
  missing visual identity.

Output STRICTLY a single JSON object, no markdown fences, no prose around it:
{
  "language": "<two-letter code of the roast language>",
  "den_score": <float 0-10, one decimal, honest>,
  "one_liner": "<the single most quotable jab about this document>",
  "brand_verdict": {
    "keep": <true if the brand signals are coherent enough to preserve>,
    "comment": "<one sharp sentence on the brand>"
  },
  "top_sins": ["<3-5 worst offenses, one line each>"],
  "sections": [
    {
      "index": <unit index>,
      "title": "<unit title or short label>",
      "score": <int 0-10>,
      "roast": "<1-2 sentences, sharp>",
      "fix": "<1 sentence, concrete and actionable>"
    }
  ],
  "summary": "<3-4 sentences: overall verdict + the path to redemption>"
}
"""

FIX_SYSTEM = """\
You are den-AI, an opinionated document surgeon. You receive the extracted
content of a PPTX or DOCX plus a roast report listing its flaws. Rebuild the
document: cut filler, merge redundant units, sharpen titles into takeaways,
turn walls of text into tight bullets, keep all factual content.

Language rule: keep the document's original language.

Output STRICTLY a single JSON object, no markdown fences, no prose around it.

For kind "pptx":
{
  "kind": "pptx",
  "use_original_brand": <true if brand_verdict.keep was true>,
  "slides": [
    {
      "layout": "title" | "section" | "content",
      "title": "<assertive takeaway title>",
      "bullets": ["<max 5 bullets, max 12 words each>"],
      "notes": "<speaker notes: what to actually say>"
    }
  ]
}

For kind "docx":
{
  "kind": "docx",
  "use_original_brand": <true if brand_verdict.keep was true>,
  "title": "<document title>",
  "blocks": [
    {"type": "heading", "level": <1-3>, "text": "..."},
    {"type": "paragraph", "text": "..."},
    {"type": "bullets", "items": ["...", "..."]}
  ]
}
"""


async def _run(prompt: str, system_prompt: str, model: str) -> str:
    options = ClaudeAgentOptions(
        system_prompt=system_prompt,
        model=model,
        setting_sources=[],
        allowed_tools=[],
        max_turns=1,
    )
    chunks: list[str] = []
    result: str | None = None
    error: str | None = None
    # No raise/return/break inside the loop: the SDK's async generator must be
    # allowed to finish on its own (ResultMessage is always the final message).
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    chunks.append(block.text)
        elif isinstance(message, ResultMessage):
            if message.is_error:
                error = message.result or message.subtype
            elif message.result:
                result = message.result
    if error is not None:
        raise RuntimeError(f"den-AI could not reach Claude: {error}")
    return result if result is not None else "".join(chunks)


def run_agent(prompt: str, system_prompt: str, model: str = DEFAULT_MODEL) -> str:
    return asyncio.run(_run(prompt, system_prompt, model))


def parse_json_response(text: str) -> dict[str, Any]:
    """Parse a JSON object out of a model response, tolerating fences/prose."""
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    else:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end == -1:
            raise ValueError(f"No JSON object in model response:\n{text[:500]}")
        text = text[start : end + 1]
    return json.loads(text)


def roast_document(extraction: dict[str, Any], model: str = DEFAULT_MODEL) -> dict[str, Any]:
    prompt = (
        "Roast this document. Extracted structure and brand signals follow as JSON:\n\n"
        + json.dumps(extraction, ensure_ascii=False, indent=2)
    )
    return parse_json_response(run_agent(prompt, ROAST_SYSTEM, model))


def fix_document(
    extraction: dict[str, Any], roast: dict[str, Any], model: str = DEFAULT_MODEL
) -> dict[str, Any]:
    prompt = (
        "Rebuild this document.\n\nExtracted content:\n"
        + json.dumps(extraction, ensure_ascii=False, indent=2)
        + "\n\nRoast report (the flaws to fix):\n"
        + json.dumps(roast, ensure_ascii=False, indent=2)
    )
    return parse_json_response(run_agent(prompt, FIX_SYSTEM, model))
