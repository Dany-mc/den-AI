"""Extract structured content and brand signals from PPTX and DOCX files."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from docx import Document
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE

# Colors that carry no brand signal
_NEUTRAL_COLORS = {"000000", "FFFFFF", "FEFEFE", "010101"}


def extract_document(path: Path) -> dict[str, Any]:
    """Return a structured view of the document: content units + brand signals."""
    suffix = path.suffix.lower()
    if suffix == ".pptx":
        return _extract_pptx(path)
    if suffix == ".docx":
        return _extract_docx(path)
    raise ValueError(f"Unsupported file type: {suffix} (expected .pptx or .docx)")


def _distill_brand(fonts: Counter, colors: Counter, has_images: bool) -> dict[str, Any]:
    """Keep only the strong, reliable signals: dominant colors and main fonts."""
    palette = [f"#{c}" for c, _ in colors.most_common(8) if c not in _NEUTRAL_COLORS][:3]
    return {
        "palette": palette,
        "fonts": [f for f, _ in fonts.most_common(3)],
        "has_images": has_images,
    }


def _extract_pptx(path: Path) -> dict[str, Any]:
    prs = Presentation(str(path))
    fonts: Counter = Counter()
    colors: Counter = Counter()
    total_images = 0
    units: list[dict[str, Any]] = []

    for index, slide in enumerate(prs.slides, start=1):
        texts: list[str] = []
        n_images = 0
        n_shapes = 0
        title = ""
        try:
            if slide.shapes.title is not None:
                title = slide.shapes.title.text.strip()
        except (AttributeError, KeyError):
            pass

        for shape in slide.shapes:
            n_shapes += 1
            if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                n_images += 1
            if not shape.has_text_frame:
                continue
            for para in shape.text_frame.paragraphs:
                for run in para.runs:
                    if run.text.strip():
                        texts.append(run.text.strip())
                    if run.font.name:
                        fonts[run.font.name] += 1
                    rgb = _run_rgb(run)
                    if rgb:
                        colors[rgb] += 1

        notes = ""
        if slide.has_notes_slide:
            notes = slide.notes_slide.notes_text_frame.text.strip()

        total_images += n_images
        units.append(
            {
                "index": index,
                "title": title,
                "texts": texts,
                "notes": notes,
                "n_shapes": n_shapes,
                "n_images": n_images,
            }
        )

    return {
        "kind": "pptx",
        "name": path.name,
        "n_units": len(units),
        "units": units,
        "brand": _distill_brand(fonts, colors, total_images > 0),
    }


def _run_rgb(run) -> str | None:
    try:
        color = run.font.color
        if color is not None and color.type is not None and color.rgb is not None:
            return str(color.rgb)
    except (AttributeError, TypeError):
        pass
    return None


def _extract_docx(path: Path) -> dict[str, Any]:
    doc = Document(str(path))
    fonts: Counter = Counter()
    colors: Counter = Counter()
    units: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    section_index = 0

    def _new_section(title: str) -> dict[str, Any]:
        nonlocal section_index
        section_index += 1
        return {"index": section_index, "title": title, "texts": [], "notes": ""}

    for para in doc.paragraphs:
        text = para.text.strip()
        style = (para.style.name or "").lower() if para.style else ""
        for run in para.runs:
            if run.font.name:
                fonts[run.font.name] += 1
            try:
                if run.font.color is not None and run.font.color.rgb is not None:
                    colors[str(run.font.color.rgb)] += 1
            except (AttributeError, TypeError):
                pass
        if not text:
            continue
        if style.startswith("heading") or style == "title":
            if current is not None:
                units.append(current)
            current = _new_section(text)
        else:
            if current is None:
                current = _new_section("(intro)")
            current["texts"].append(text)

    if current is not None:
        units.append(current)

    n_tables = len(doc.tables)
    n_images = len(doc.inline_shapes)
    return {
        "kind": "docx",
        "name": path.name,
        "n_units": len(units),
        "n_tables": n_tables,
        "units": units,
        "brand": _distill_brand(fonts, colors, n_images > 0),
    }
