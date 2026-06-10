"""denai — the CLI entry point."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
from rich.console import Console

from denai import __version__
from denai.agent import DEFAULT_MODEL, fix_document, roast_document
from denai.card import write_card
from denai.extract import extract_document
from denai.rebuild import rebuild_document
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
def roast(file: Path, model: str, no_card: bool, lang: str | None) -> None:
    """Critique FILE (.pptx or .docx) without mercy."""
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
        console.print(f"[dim]Scorecard:[/dim] {card_path}")

    console.print(f"\n[dim]Now run[/dim] [bold]denai fix {file.name}[/bold] [dim]to see it done right.[/dim]")


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

    console.print("[dim]Rebuilding…[/dim]")
    spec = fix_document(extraction, roast_result, model=model)
    out_path = file.with_name(f"{file.stem}.denai-fixed{file.suffix}")
    rebuild_document(spec, extraction, out_path)

    brand_note = (
        "kept your brand" if spec.get("use_original_brand") else "applied den style (your brand didn't make the cut)"
    )
    console.print(f"\n[green]✓[/green] Rebuilt: [bold]{out_path}[/bold] — {brand_note}.")


if __name__ == "__main__":
    main()
