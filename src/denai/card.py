"""Generate the shareable HTML scorecard for a roast."""

from __future__ import annotations

import html
from pathlib import Path
from typing import Any

_TEMPLATE = """<!DOCTYPE html>
<html lang="{language}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>den-AI roast — {name}</title>
<style>
  :root {{ --accent: {accent}; }}
  * {{ box-sizing: border-box; margin: 0; }}
  body {{
    font-family: Georgia, 'Times New Roman', serif;
    background: #14130f; color: #f4f1ea;
    display: flex; justify-content: center; padding: 48px 16px;
  }}
  .card {{
    max-width: 640px; width: 100%;
    background: #1d1b16; border: 1px solid #3a372e; border-radius: 16px;
    padding: 40px; box-shadow: 0 24px 64px rgba(0,0,0,.5);
  }}
  .label {{
    font-family: ui-monospace, Menlo, monospace; font-size: 12px;
    letter-spacing: .2em; text-transform: uppercase; color: #8d8775;
  }}
  h1 {{ font-size: 22px; font-weight: normal; margin: 8px 0 28px; color: #cfc9b8; }}
  .score {{ display: flex; align-items: baseline; gap: 14px; margin-bottom: 8px; }}
  .score b {{ font-size: 72px; color: var(--accent); font-style: italic; }}
  .score span {{ font-size: 20px; color: #8d8775; }}
  .bar {{ height: 6px; background: #3a372e; border-radius: 3px; margin: 12px 0 28px; }}
  .bar i {{ display: block; height: 100%; width: {pct}%; background: var(--accent); border-radius: 3px; }}
  blockquote {{
    font-size: 19px; font-style: italic; line-height: 1.5;
    border-left: 3px solid var(--accent); padding-left: 16px; margin-bottom: 28px;
  }}
  ul {{ list-style: none; padding: 0; }}
  li {{ padding: 7px 0 7px 26px; position: relative; line-height: 1.45; color: #d8d3c4; }}
  li::before {{ content: "✗"; position: absolute; left: 0; color: var(--accent); }}
  footer {{
    margin-top: 32px; padding-top: 18px; border-top: 1px solid #3a372e;
    font-family: ui-monospace, Menlo, monospace; font-size: 12px; color: #8d8775;
    display: flex; justify-content: space-between;
  }}
</style>
</head>
<body>
  <div class="card">
    <div class="label">den-AI roast</div>
    <h1>{name}</h1>
    <div class="score"><b>{score:.1f}</b><span>/ 10</span></div>
    <div class="bar"><i></i></div>
    <blockquote>“{one_liner}”</blockquote>
    <div class="label">top sins</div>
    <ul>{sins}</ul>
    <footer><span>github.com/Dany-mc/den-AI</span><span>roasted, then fixed.</span></footer>
  </div>
</body>
</html>
"""


def write_card(roast: dict[str, Any], source_name: str, out_path: Path) -> Path:
    score = float(roast.get("den_score", 0))
    accent = "#7fb069" if score >= 7 else "#e6b450" if score >= 5 else "#e05d44"
    sins = "".join(
        f"<li>{html.escape(sin)}</li>" for sin in roast.get("top_sins", [])[:5]
    )
    out_path.write_text(
        _TEMPLATE.format(
            language=html.escape(roast.get("language", "en")),
            name=html.escape(source_name),
            score=score,
            pct=max(2, min(100, int(score * 10))),
            accent=accent,
            one_liner=html.escape(roast.get("one_liner", "")),
            sins=sins,
        ),
        encoding="utf-8",
    )
    return out_path
