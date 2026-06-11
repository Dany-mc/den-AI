"""denai — the CLI entry point."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
from rich.console import Console

from denai import __version__
from denai.agent import (
    DEFAULT_MODEL,
    build_report,
    fix_document,
    plan_edits,
    roast_document,
)
from denai.card import write_card
from denai.card_png import write_card_png
from denai.editor import apply_edits
from denai.extract import extract_csv, extract_document
from denai.rebuild import fixed_suffix, rebuild_document
from denai.report import render_terminal, write_markdown

console = Console()


def _load_document(file: Path) -> dict:
    try:
        return extract_document(file)
    except ValueError as exc:
        console.print(f"[red]✗[/red] {exc}")
        sys.exit(1)


@click.group()
@click.version_option(__version__, prog_name="denai")
def main() -> None:
    """den-AI: roasts your decks and reports, then rebuilds them better."""
    from denai.auth import apply_stored_key

    apply_stored_key()


@main.command()
@click.argument("file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--model", default=DEFAULT_MODEL, show_default=True, help="Claude model to use.")
@click.option("--no-card", is_flag=True, help="Skip the shareable HTML scorecard.")
@click.option(
    "--lang",
    type=click.Choice(["it", "en", "es"]),
    default=None,
    help="Roast language (default: the document's own language).",
)
@click.option(
    "--diff",
    "diff_",
    is_flag=True,
    help="Roast the .denai-fixed version and compare it with the original roast.",
)
def roast(file: Path, model: str, no_card: bool, lang: str | None, diff_: bool) -> None:
    """Critique FILE (.pptx, .docx, .pdf or .md) without mercy."""
    if diff_:
        _diff(file, model, lang)
        return

    extraction = _load_document(file)
    console.print(
        f"[dim]den-AI is reading [bold]{file.name}[/bold] "
        f"({extraction['n_units']} {'slides' if extraction['kind'] == 'pptx' else 'sections'})… "
        "preparing the verdict.[/dim]"
    )

    result = roast_document(extraction, model=model, language=lang)
    render_terminal(result, console)

    json_path = file.with_suffix(".denai.json")
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path = write_markdown(result, file.name, file.with_suffix(".denai.md"))
    console.print(f"[dim]Report:[/dim] {md_path}")

    if not no_card:
        card_path = write_card(result, file.name, file.with_suffix(".denai.html"))
        png_path = write_card_png(result, file.name, file.with_suffix(".denai.png"))
        console.print(f"[dim]Scorecard:[/dim] {card_path} · {png_path}")

    console.print(f"\n[dim]Now run[/dim] [bold]denai fix {file.name}[/bold] [dim]to see it done right.[/dim]")


def _diff(file: Path, model: str, lang: str | None) -> None:
    """Roast the fixed version and show before/after."""
    before_path = file.with_suffix(".denai.json")
    fixed_path = file.with_name(f"{file.stem}.denai-fixed{fixed_suffix(file.suffix.lower())}")
    if not before_path.exists():
        console.print(f"[red]✗[/red] No roast on file ({before_path.name}). Run [bold]denai roast[/bold] first.")
        sys.exit(1)
    if not fixed_path.exists():
        console.print(f"[red]✗[/red] No fixed version ({fixed_path.name}). Run [bold]denai fix[/bold] first.")
        sys.exit(1)

    before = json.loads(before_path.read_text(encoding="utf-8"))
    console.print(f"[dim]den-AI is re-judging its own work on [bold]{fixed_path.name}[/bold]…[/dim]")
    after = roast_document(_load_document(fixed_path), model=model, language=lang)

    b, a = float(before.get("den_score", 0)), float(after.get("den_score", 0))
    delta = a - b
    color = "green" if delta > 0 else "red" if delta < 0 else "yellow"
    from rich.panel import Panel

    verdict = (
        "Redemption achieved." if delta >= 2
        else "Better. den-AI accepts partial credit." if delta > 0
        else "No improvement. Awkward — for everyone involved."
    )
    console.print()
    console.print(
        Panel(
            f"[bold]den score: {b:.1f} → {a:.1f}[/bold]  "
            f"[{color}]({'+' if delta >= 0 else ''}{delta:.1f})[/{color}]\n\n"
            f"[dim]before:[/dim] [italic]“{before.get('one_liner', '')}”[/italic]\n"
            f"[dim]after:[/dim]  [italic]“{after.get('one_liner', '')}”[/italic]\n\n"
            f"{verdict}",
            title="[bold]before / after[/bold]",
            border_style=color,
        )
    )


@main.command()
@click.option("--port", default=8765, show_default=True, help="Port for den-AI studio.")
@click.option("--model", default=DEFAULT_MODEL, show_default=True, help="Claude model to use.")
@click.option("--no-browser", is_flag=True, help="Don't open the browser automatically.")
def web(port: int, model: str, no_browser: bool) -> None:
    """Open den-AI studio: the web UI, on localhost."""
    import threading
    import webbrowser

    import uvicorn

    from denai.web.server import create_app

    url = f"http://127.0.0.1:{port}"
    console.print(f"\n[bold]den-AI studio[/bold] → [link={url}]{url}[/link]  [dim](Ctrl+C to stop)[/dim]\n")
    if not no_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    uvicorn.run(create_app(model=model), host="127.0.0.1", port=port, log_level="warning")


@main.command()
@click.argument("file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--model", default=DEFAULT_MODEL, show_default=True, help="Claude model to use.")
def fix(file: Path, model: str) -> None:
    """Rebuild FILE the way it should have been built."""
    extraction = _load_document(file)

    json_path = file.with_suffix(".denai.json")
    if json_path.exists():
        roast_result = json.loads(json_path.read_text(encoding="utf-8"))
        console.print(f"[dim]Using existing roast: {json_path.name}[/dim]")
    else:
        console.print("[dim]No roast on file — den-AI judges before it heals.[/dim]")
        roast_result = roast_document(extraction, model=model)
        json_path.write_text(
            json.dumps(roast_result, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    out_path = file.with_name(f"{file.stem}.denai-fixed{fixed_suffix(file.suffix.lower())}")
    kind = extraction["kind"]

    if kind in ("pptx", "docx"):
        # Surgical mode: edit the original in place — design untouched.
        console.print("[dim]Operating… your design stays on the table.[/dim]")
        plan = plan_edits(extraction, roast_result, model=model)
        applied = apply_edits(plan.get("edits", []), file, out_path, kind)
        console.print(
            f"\n[green]✓[/green] Edited: [bold]{out_path}[/bold] — "
            f"{applied} surgical edits, your design untouched."
        )
        for line in plan.get("changelog", []):
            console.print(f"  [green]·[/green] {line}")
    else:
        # No design to preserve (pdf/md): rebuild as a clean document.
        console.print("[dim]Rebuilding…[/dim]")
        spec = fix_document(extraction, roast_result, model=model)
        rebuild_document(spec, extraction, out_path)
        console.print(f"\n[green]✓[/green] Rebuilt: [bold]{out_path}[/bold].")


@main.command()
@click.argument("file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "--to",
    "target",
    type=click.Choice(["docx", "pptx"]),
    default="docx",
    show_default=True,
    help="Output format of the report.",
)
@click.option("--model", default=DEFAULT_MODEL, show_default=True, help="Claude model to use.")
@click.option(
    "--lang",
    type=click.Choice(["it", "en", "es"]),
    default=None,
    help="Report language (default: the data's own language).",
)
def report(file: Path, target: str, model: str, lang: str | None) -> None:
    """Turn a raw CSV into a den-approved report (charts included)."""
    if file.suffix.lower() != ".csv":
        console.print("[red]✗[/red] `denai report` eats .csv files.")
        sys.exit(1)
    try:
        data = extract_csv(file)
    except ValueError as exc:
        console.print(f"[red]✗[/red] {exc}")
        sys.exit(1)

    console.print(
        f"[dim]den-AI is reading [bold]{file.name}[/bold] "
        f"({data['n_rows']} rows × {len(data['headers'])} columns)… building the report it deserves.[/dim]"
    )
    spec = build_report(data, target, model=model, language=lang)
    out_path = file.with_name(f"{file.stem}.denai-report.{target}")
    rebuild_document(spec, {"kind": target, "brand": {}}, out_path)
    console.print(f"\n[green]✓[/green] Report: [bold]{out_path}[/bold] — numbers first, filler nowhere.")


if __name__ == "__main__":
    main()
