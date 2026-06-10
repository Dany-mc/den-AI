"""Render the shareable scorecard as a PNG with Pillow (no browser needed)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

_W = 1080
_PAD = 72
_BG = (20, 19, 15)
_CARD = (29, 27, 22)
_HAIRLINE = (58, 55, 46)
_TEXT = (244, 241, 234)
_MUTED = (141, 135, 117)

_FONT_DIRS = [
    "/System/Library/Fonts/Supplemental",  # macOS
    "/usr/share/fonts/truetype/dejavu",  # Linux
    "C:/Windows/Fonts",  # Windows
]
_SERIF = ["Georgia.ttf", "Georgia Bold.ttf", "DejaVuSerif.ttf", "georgia.ttf", "times.ttf"]
_SERIF_ITALIC = ["Georgia Italic.ttf", "DejaVuSerif-Italic.ttf", "georgiai.ttf", "timesi.ttf"]
_MONO = ["Menlo.ttc", "Courier New.ttf", "DejaVuSansMono.ttf", "consola.ttf"]


def _font(candidates: list[str], size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for directory in _FONT_DIRS:
        for name in candidates:
            try:
                return ImageFont.truetype(str(Path(directory) / name), size)
            except OSError:
                continue
    return ImageFont.load_default(size)


def _accent(score: float) -> tuple[int, int, int]:
    if score >= 7:
        return (127, 176, 105)
    if score >= 5:
        return (230, 180, 80)
    return (224, 93, 68)


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    lines: list[str] = []
    line = ""
    for word in text.split():
        candidate = f"{line} {word}".strip()
        if draw.textlength(candidate, font=font) <= max_width:
            line = candidate
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def write_card_png(roast: dict[str, Any], source_name: str, out_path: Path) -> Path:
    score = float(roast.get("den_score", 0))
    accent = _accent(score)
    sins = roast.get("top_sins", [])[:5]

    label_f = _font(_MONO, 22)
    name_f = _font(_SERIF, 34)
    score_f = _font(_SERIF_ITALIC, 130)
    denom_f = _font(_SERIF, 36)
    quote_f = _font(_SERIF_ITALIC, 40)
    sin_f = _font(_SERIF, 30)

    # Draw on a tall canvas, crop to content at the end.
    img = Image.new("RGB", (_W, 2400), _BG)
    draw = ImageDraw.Draw(img)
    inner_w = _W - 2 * _PAD

    y = _PAD + 24
    draw.text((_PAD, y), "D E N - A I   R O A S T", font=label_f, fill=_MUTED)
    y += 48
    draw.text((_PAD, y), source_name, font=name_f, fill=(207, 201, 184))
    y += 84

    score_text = f"{score:.1f}"
    draw.text((_PAD, y), score_text, font=score_f, fill=accent)
    score_w = draw.textlength(score_text, font=score_f)
    draw.text((_PAD + score_w + 22, y + 86), "/ 10", font=denom_f, fill=_MUTED)
    y += 168

    # score bar
    bar_w = inner_w
    draw.rounded_rectangle([_PAD, y, _PAD + bar_w, y + 10], radius=5, fill=_HAIRLINE)
    fill_w = max(12, int(bar_w * min(score, 10) / 10))
    draw.rounded_rectangle([_PAD, y, _PAD + fill_w, y + 10], radius=5, fill=accent)
    y += 52

    # quote with accent rule
    quote_lines = _wrap(draw, f"“{roast.get('one_liner', '')}”", quote_f, inner_w - 36)
    quote_top = y
    for line in quote_lines:
        draw.text((_PAD + 28, y), line, font=quote_f, fill=_TEXT)
        y += 56
    draw.rounded_rectangle([_PAD, quote_top + 6, _PAD + 6, y - 8], radius=3, fill=accent)
    y += 36

    draw.text((_PAD, y), "T O P   S I N S", font=label_f, fill=_MUTED)
    y += 50
    for sin in sins:
        draw.text((_PAD, y), "×", font=sin_f, fill=accent)
        for line in _wrap(draw, sin, sin_f, inner_w - 48):
            draw.text((_PAD + 44, y), line, font=sin_f, fill=(216, 211, 196))
            y += 44
        y += 10
    y += 24

    draw.line([_PAD, y, _W - _PAD, y], fill=_HAIRLINE, width=2)
    y += 26
    draw.text((_PAD, y), "github.com/Dany-mc/den-AI", font=label_f, fill=_MUTED)
    tagline = "roasted, then fixed."
    draw.text(
        (_W - _PAD - draw.textlength(tagline, font=label_f), y),
        tagline,
        font=label_f,
        fill=_MUTED,
    )
    y += 60

    img = img.crop((0, 0, _W, y))
    framed = Image.new("RGB", (_W, y), _BG)
    framed.paste(img, (0, 0))
    framed.save(out_path, "PNG")
    return out_path
