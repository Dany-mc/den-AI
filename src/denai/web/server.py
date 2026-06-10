"""FastAPI backend for den-AI studio.

Endpoints are deliberately sync (`def`, not `async def`): FastAPI runs them in
a worker thread, where the agent module's asyncio.run() is safe to call.
"""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse

from denai import __version__
from denai.agent import DEFAULT_MODEL, fix_document, roast_document
from denai.extract import extract_document
from denai.rebuild import rebuild_document

STATIC_DIR = Path(__file__).parent / "static"
_ALLOWED_SUFFIXES = {".pptx", ".docx"}


def create_app(model: str = DEFAULT_MODEL) -> FastAPI:
    app = FastAPI(title="den-AI studio", version=__version__)
    jobs: dict[str, dict[str, Any]] = {}
    workdir = Path(tempfile.mkdtemp(prefix="denai-studio-"))

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return (STATIC_DIR / "index.html").read_text(encoding="utf-8")

    @app.get("/api/info")
    def info() -> dict[str, str]:
        return {"version": __version__, "model": model}

    @app.post("/api/roast")
    def roast(
        file: UploadFile = File(...), language: str | None = Form(None)
    ) -> dict[str, Any]:
        name = file.filename or "document"
        suffix = Path(name).suffix.lower()
        if suffix not in _ALLOWED_SUFFIXES:
            raise HTTPException(400, "den-AI only judges .pptx and .docx files.")
        if language not in (None, "it", "en", "es"):
            raise HTTPException(400, "Supported languages: it, en, es.")

        job_id = uuid.uuid4().hex[:12]
        src = workdir / f"{job_id}{suffix}"
        src.write_bytes(file.file.read())

        try:
            extraction = extract_document(src)
            roast_result = roast_document(extraction, model=model, language=language)
        except Exception as exc:  # surfaced to the UI as-is
            raise HTTPException(502, f"{exc}") from exc

        jobs[job_id] = {"name": name, "extraction": extraction, "roast": roast_result}
        return {
            "job_id": job_id,
            "name": name,
            "kind": extraction["kind"],
            "n_units": extraction["n_units"],
            "roast": roast_result,
        }

    @app.post("/api/fix/{job_id}")
    def fix(job_id: str) -> dict[str, Any]:
        job = jobs.get(job_id)
        if job is None:
            raise HTTPException(404, "Unknown job — roast the file first.")

        try:
            spec = fix_document(job["extraction"], job["roast"], model=model)
            suffix = Path(job["name"]).suffix.lower()
            fixed = workdir / f"{job_id}-fixed{suffix}"
            rebuild_document(spec, job["extraction"], fixed)
        except Exception as exc:
            raise HTTPException(502, f"{exc}") from exc

        job["fixed"] = fixed
        return {
            "job_id": job_id,
            "use_original_brand": bool(spec.get("use_original_brand")),
            "download": f"/api/download/{job_id}",
        }

    @app.get("/api/download/{job_id}")
    def download(job_id: str) -> FileResponse:
        job = jobs.get(job_id)
        if job is None or "fixed" not in job:
            raise HTTPException(404, "Nothing to download — fix the file first.")
        stem = Path(job["name"]).stem
        suffix = Path(job["name"]).suffix.lower()
        return FileResponse(
            job["fixed"],
            filename=f"{stem}.denai-fixed{suffix}",
            media_type="application/octet-stream",
        )

    return app
