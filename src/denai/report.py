"""Render the roast: rich terminal output + Markdown report."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table


def _score_color(score: float) -> str:
    if score >= 7:
        return "green"
    if score >= 5:
        return "yellow"
    return "red"


def render_terminal(roast: dict[str, Any], console: Console | None = None) -> None:
    console = console or Console()
    score = float(roast.get("den_score", 0))
    color = _score_color(score)

    console.print()
    console.print(
        Panel(
            f"[bold {color}]den score: {score:.1f}/10[/]\n\n"
            f"[italic]“{roast.get('one_liner', '')}”[/italic]",
            title="[bold]den-AI verdict[/bold]",
            border_style=color,
        )
    )

    brand = roast.get("brand_verdict", {})
    verdict = "[green]keeping your brand[/]" if brand.get("keep") else "[red]your brand is part of the problem[/]"
    console.print(f"\n[bold]Brand:[/bold] {verdict} — {brand.get('comment', '')}")

    sins = roast.get("top_sins", [])
    if sins:
        console.print("\n[bold]Top sins:[/bold]")
        for sin in sins:
            console.print(f"  [red]✗[/red] {sin}")

    sections = roast.get("sections", [])
    if sections:
        table = Table(title="Section by section", show_lines=False, header_style="bold")
        table.add_column("#", justify="right", width=3)
        table.add_column("Title", max_width=28)
        table.add_column("Score", justify="center", width=5)
        table.add_column("Roast / Fix")
        for s in sections:
            s_score = int(s.get("score", 0))
            table.add_row(
                str(s.get("index", "?")),
                s.get("title", ""),
                f"[{_score_color(s_score)}]{s_score}[/]",
                f"{s.get('roast', '')}\n[dim]→ {s.get('fix', '')}[/dim]",
            )
        console.print()
        console.print(table)

    console.print(f"\n[bold]Summary:[/bold] {roast.get('summary', '')}\n")


def write_markdown(roast: dict[str, Any], source_name: str, out_path: Path) -> Path:
    score = float(roast.get("den_score", 0))
    brand = roast.get("brand_verdict", {})
    lines = [
        f"# den-AI roast — {source_name}",
        "",
        f"**den score: {score:.1f}/10**",
        "",
        f"> “{roast.get('one_liner', '')}”",
        "",
        "## Brand verdict",
        "",
        f"- **Keep brand:** {'yes' if brand.get('keep') else 'no'}",
        f"- {brand.get('comment', '')}",
        "",
        "## Top sins",
        "",
    ]
    lines += [f"- {sin}" for sin in roast.get("top_sins", [])]
    lines += ["", "## Section by section", ""]
    for s in roast.get("sections", []):
        lines += [
            f"### {s.get('index', '?')}. {s.get('title', '')} — {s.get('score', '?')}/10",
            "",
            f"{s.get('roast', '')}",
            "",
            f"**Fix:** {s.get('fix', '')}",
            "",
        ]
    lines += ["## Summary", "", roast.get("summary", ""), "", "---", "", "_Roasted by [den-AI](https://github.com/Dany-mc/den-AI)._", ""]
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path
