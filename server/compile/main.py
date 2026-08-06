from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

app = FastAPI(title="latex-compile-service", version="0.1.0")

ENGINE_FLAGS = {
    "pdflatex": "-pdf",
    "xelatex": "-xelatex",
    "lualatex": "-lualatex",
}

COMPILE_TIMEOUT_SECONDS = int(os.getenv("COMPILE_TIMEOUT_SECONDS", "120"))


class CompileRequest(BaseModel):
    tex: str = Field(..., description="Full LaTeX source to compile.")
    engine: str = Field("pdflatex", description="pdflatex | xelatex | lualatex")
    jobname: str = Field("resume", description="Base name for the compiled artifacts.")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/compile")
def compile_tex(req: CompileRequest):
    engine_flag = ENGINE_FLAGS.get(req.engine)
    if engine_flag is None:
        return JSONResponse(
            status_code=400,
            content={"detail": f"unsupported engine '{req.engine}'", "supported": list(ENGINE_FLAGS)},
        )

    workdir = Path(tempfile.mkdtemp(prefix="latex-"))
    try:
        tex_path = workdir / f"{req.jobname}.tex"
        tex_path.write_text(req.tex, encoding="utf-8")

        proc = subprocess.run(
            ["latexmk", engine_flag, "-interaction=nonstopmode", "-f",
             "-no-shell-escape", f"-jobname={req.jobname}", tex_path.name],
            cwd=workdir,
            capture_output=True,
            text=True,
            timeout=COMPILE_TIMEOUT_SECONDS,
        )

        # pdflatex/latexmk exit nonzero whenever any error was logged, even
        # ones it auto-corrected and recovered from (e.g. a unitless \vspace
        # gets "pt" inserted) — same as Overleaf, which doesn't halt on these
        # either. A produced PDF is the real signal of success; a genuinely
        # fatal error (unrecoverable, like a missing \begin{document}) never
        # produces one even with -f, so this doesn't hide real failures.
        pdf_path = workdir / f"{req.jobname}.pdf"
        if pdf_path.exists():
            return Response(
                content=pdf_path.read_bytes(),
                media_type="application/pdf",
                headers={"Content-Disposition": f'inline; filename="{req.jobname}.pdf"'},
            )

        log = _read_log(workdir, req.jobname, proc)
        return JSONResponse(status_code=422, content={"detail": "compile failed", "log": log})

    except subprocess.TimeoutExpired:
        return JSONResponse(
            status_code=504,
            content={"detail": f"compile timed out after {COMPILE_TIMEOUT_SECONDS}s"},
        )
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def _read_log(workdir: Path, jobname: str, proc: subprocess.CompletedProcess) -> str:
    log_file = workdir / f"{jobname}.log"
    if log_file.exists():
        return log_file.read_text(encoding="utf-8", errors="replace")
    return (proc.stdout or "") + "\n" + (proc.stderr or "")
