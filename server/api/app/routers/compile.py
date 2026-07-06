from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from ..compile_client import compile_tex

router = APIRouter(prefix="/compile", tags=["compile"])


class CompileIn(BaseModel):
    tex: str
    engine: str = "pdflatex"
    jobname: str = "resume"


@router.post("")
async def compile_endpoint(body: CompileIn, request: Request):
    resp = await compile_tex(request.app.state.http, body.tex, body.engine, body.jobname)
    if resp.status_code == 200:
        return Response(content=resp.content, media_type="application/pdf")
    return JSONResponse(status_code=resp.status_code, content=resp.json())
