"""QueueSift HTTP surface (Slice 3a: read-only shadow digest plus health)."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Response
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from app import shadow_ui
from app.db import (
    count_issues,
    count_proposals,
    get_proposal,
    init_db,
    list_proposals,
    make_engine,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db(make_engine())
    yield


app = FastAPI(title="QueueSift", version="0.1.0", lifespan=lifespan)

SCOPE = "astral-sh/uv backlog sweep (150-issue frozen cohort)"
REPORTS_DIR = Path("evals/reports")


def _engine():
    return make_engine()


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "queuesift"}


@app.get("/", response_class=HTMLResponse)
def overview() -> str:
    engine = _engine()
    return shadow_ui.overview_html(count_issues(engine), count_proposals(engine), SCOPE)


@app.get("/digest", response_class=HTMLResponse)
def digest() -> str:
    return shadow_ui.digest_html(list_proposals(_engine()))


@app.get("/proposals/{issue_number}", response_class=HTMLResponse, response_model=None)
def proposal_detail(issue_number: int) -> Response:
    proposal = get_proposal(_engine(), issue_number)
    if proposal is None:
        return JSONResponse({"detail": "proposal not found"}, status_code=404)
    return HTMLResponse(shadow_ui.proposal_html(proposal))


@app.get("/evals", response_class=HTMLResponse)
def evals_index() -> str:
    return shadow_ui.evals_html()


@app.get("/evals/{name}", response_model=None)
def eval_report(name: str) -> Response:
    allowed = {report for report, _ in shadow_ui.EVAL_REPORTS}
    if name not in allowed:
        return JSONResponse({"detail": "unknown report"}, status_code=404)
    path = REPORTS_DIR / name
    if not path.exists():
        return JSONResponse({"detail": "report not found on disk"}, status_code=404)
    return FileResponse(path, media_type="application/json")
