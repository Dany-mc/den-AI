"""Tests for roadmap features: PDF/MD/CSV input, charts, PNG card, suffix rules."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import denai.web.server as server
from denai.card_png import write_card_png
from denai.extract import extract_csv, extract_document
from denai.rebuild import fixed_suffix, rebuild_document, render_chart
from denai.web.server import create_app

MOCK_ROAST = {
    "language": "en",
    "den_score": 3.8,
    "one_liner": "Twelve slides to say one number went up.",
    "brand_verdict": {"keep": False, "comment": "No brand to save."},
    "top_sins": ["Wall of text on slide 2"],
    "sections": [
        {"index": 1, "title": "Q3", "score": 4, "roast": "Meh.", "fix": "Lead with the number."}
    ],
    "summary": "Cut it down.",
}

MD_SAMPLE = """\
# Quarterly report

Intro paragraph nobody reads.

## Numbers

Revenue went up.

```
code fences are skipped
```

## Conclusions

All good.
"""


def test_extract_md(tmp_path: Path) -> None:
    path = tmp_path / "report.md"
    path.write_text(MD_SAMPLE, encoding="utf-8")
    result = extract_document(path)
    assert result["kind"] == "md"
    titles = [u["title"] for u in result["units"]]
    assert titles == ["Quarterly report", "Numbers", "Conclusions"]
    assert "code fences are skipped" not in str(result["units"])


def test_extract_pdf(tmp_path: Path) -> None:
    # Build a small two-page PDF with matplotlib (text is extractable).
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages

    path = tmp_path / "doc.pdf"
    with PdfPages(str(path)) as pdf:
        for page_text in ("First page title", "Second page title"):
            fig = plt.figure(figsize=(8, 6))
            fig.text(0.1, 0.8, page_text, fontsize=20)
            pdf.savefig(fig)
            plt.close(fig)

    result = extract_document(path)
    assert result["kind"] == "pdf"
    assert result["n_units"] == 2


def test_extract_csv(tmp_path: Path) -> None:
    path = tmp_path / "data.csv"
    path.write_text("month,revenue\nJan,100\nFeb,140\nMar,90\n", encoding="utf-8")
    data = extract_csv(path)
    assert data["headers"] == ["month", "revenue"]
    assert data["n_rows"] == 3
    assert data["rows"][1] == ["Feb", "140"]


def test_render_chart(tmp_path: Path) -> None:
    out = render_chart(
        {"type": "bar", "title": "Revenue", "labels": ["Jan", "Feb"], "values": [100, 140]},
        "#E05D44",
        tmp_path / "chart.png",
    )
    assert out is not None and out.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    # malformed spec → None, no crash
    assert render_chart({"labels": ["a"], "values": []}, "#E05D44", tmp_path / "x.png") is None


def test_rebuild_pptx_with_chart(tmp_path: Path) -> None:
    spec = {
        "kind": "pptx",
        "use_original_brand": False,
        "slides": [
            {
                "layout": "content",
                "title": "Revenue up",
                "bullets": ["Good quarter"],
                "chart": {"type": "line", "labels": ["Q1", "Q2"], "values": [1, 2]},
            }
        ],
    }
    out = rebuild_document(spec, {"kind": "pptx", "brand": {}}, tmp_path / "out.pptx")
    rebuilt = extract_document(out)
    assert rebuilt["units"][0]["n_images"] == 1  # the chart landed on the slide


def test_fixed_suffix_mapping() -> None:
    assert fixed_suffix(".pptx") == ".pptx"
    assert fixed_suffix(".docx") == ".docx"
    assert fixed_suffix(".pdf") == ".docx"
    assert fixed_suffix(".md") == ".docx"


def test_write_card_png(tmp_path: Path) -> None:
    out = write_card_png(MOCK_ROAST, "deck.pptx", tmp_path / "card.png")
    assert out.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(
        server, "roast_document", lambda extraction, model, language=None: MOCK_ROAST
    )
    monkeypatch.setattr(
        server,
        "fix_document",
        lambda extraction, roast, model: {
            "kind": "docx",
            "use_original_brand": False,
            "title": "Fixed",
            "blocks": [{"type": "paragraph", "text": "Better."}],
        },
    )
    return TestClient(create_app())


def test_web_md_roast_fix_and_card(client: TestClient, tmp_path: Path) -> None:
    md = tmp_path / "notes.md"
    md.write_text(MD_SAMPLE, encoding="utf-8")
    with md.open("rb") as fh:
        res = client.post("/api/roast", files={"file": ("notes.md", fh)})
    assert res.status_code == 200
    job_id = res.json()["job_id"]

    res = client.get(f"/api/card/{job_id}.png")
    assert res.status_code == 200
    assert res.content[:8] == b"\x89PNG\r\n\x1a\n"

    assert client.post(f"/api/fix/{job_id}").status_code == 200
    res = client.get(f"/api/download/{job_id}")
    assert res.headers["content-disposition"].endswith('notes.denai-fixed.docx"')
