"""Rebuild documents from a den-AI fix spec, applying brand or den style."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from docx import Document
from docx.shared import Pt as DocxPt
from docx.shared import RGBColor as DocxRGB
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Pt

# den style: the opinionated fallback identity when the original brand is beyond saving
DEN_STYLE = {
    "palette": ["#1D1B16", "#E05D44", "#8D8775"],
    "fonts": ["Georgia"],
}


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _pick_brand(spec: dict[str, Any], extraction: dict[str, Any]) -> dict[str, Any]:
    original = extraction.get("brand", {})
    if spec.get("use_original_brand") and original.get("palette"):
        return {
            "palette": original["palette"],
            "fonts": original.get("fonts") or DEN_STYLE["fonts"],
        }
    return DEN_STYLE


def rebuild_document(spec: dict[str, Any], extraction: dict[str, Any], out_path: Path) -> Path:
    kind = spec.get("kind", extraction.get("kind"))
    if kind == "pptx":
        return _rebuild_pptx(spec, extraction, out_path)
    if kind == "docx":
        return _rebuild_docx(spec, extraction, out_path)
    raise ValueError(f"Unsupported rebuild kind: {kind}")


def _rebuild_pptx(spec: dict[str, Any], extraction: dict[str, Any], out_path: Path) -> Path:
    brand = _pick_brand(spec, extraction)
    accent = _hex_to_rgb(brand["palette"][0])
    font = brand["fonts"][0]

    prs = Presentation()
    layouts = {
        "title": prs.slide_layouts[0],
        "content": prs.slide_layouts[1],
        "section": prs.slide_layouts[2],
    }

    for slide_spec in spec.get("slides", []):
        layout = layouts.get(slide_spec.get("layout", "content"), layouts["content"])
        slide = prs.slides.add_slide(layout)

        if slide.shapes.title is not None:
            title_shape = slide.shapes.title
            title_shape.text = slide_spec.get("title", "")
            for para in title_shape.text_frame.paragraphs:
                for run in para.runs:
                    run.font.name = font
                    run.font.color.rgb = RGBColor(*accent)
                    run.font.bold = True

        bullets = slide_spec.get("bullets") or []
        body = next(
            (ph for ph in slide.placeholders if ph.placeholder_format.idx == 1), None
        )
        if body is not None and bullets:
            tf = body.text_frame
            tf.clear()
            for i, bullet in enumerate(bullets):
                para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
                para.text = bullet
                para.level = 0
                for run in para.runs:
                    run.font.name = font
                    run.font.size = Pt(20)

        notes = slide_spec.get("notes")
        if notes:
            slide.notes_slide.notes_text_frame.text = notes

    prs.save(str(out_path))
    return out_path


def _rebuild_docx(spec: dict[str, Any], extraction: dict[str, Any], out_path: Path) -> Path:
    brand = _pick_brand(spec, extraction)
    accent = _hex_to_rgb(brand["palette"][0])
    font = brand["fonts"][0]

    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = font
    style.font.size = DocxPt(11)

    title = spec.get("title")
    if title:
        heading = doc.add_heading(title, level=0)
        for run in heading.runs:
            run.font.color.rgb = DocxRGB(*accent)

    for block in spec.get("blocks", []):
        btype = block.get("type")
        if btype == "heading":
            level = min(max(int(block.get("level", 1)), 1), 3)
            heading = doc.add_heading(block.get("text", ""), level=level)
            for run in heading.runs:
                run.font.color.rgb = DocxRGB(*accent)
        elif btype == "paragraph":
            doc.add_paragraph(block.get("text", ""))
        elif btype == "bullets":
            for item in block.get("items", []):
                doc.add_paragraph(item, style="List Bullet")

    doc.save(str(out_path))
    return out_path
