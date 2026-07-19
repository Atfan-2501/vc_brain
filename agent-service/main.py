"""VC Brain agent service — FastAPI. The 7 contract endpoints, thin.
Each endpoint validates input, delegates to pipeline/agents, returns contract-shaped JSON.
While USE_STUBS=true it returns canned data so you can prove integration before any AI logic.
"""
import uuid
import traceback
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import config
import stub_data
from contracts import (
    ThesisIn, ThesisOut, ApplyOut, OpportunitiesOut, OpportunityDetail,
    QueryIn, QueryOut, ScanIn, ScanOut, FounderOut, ReasoningLogOut,
)

app = FastAPI(title="VC Brain Agent Service", version="0.1.0")

# Lovable frontend is on another origin — allow it.
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


@app.exception_handler(Exception)
async def debug_exception_handler(request, exc):
    """Surface the real error in the response when DEBUG_ERRORS=true (skips HTTPExceptions)."""
    if isinstance(exc, HTTPException):
        return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})
    if config.DEBUG_ERRORS:
        return JSONResponse(status_code=500, content={
            "error": type(exc).__name__, "detail": str(exc),
            "trace": traceback.format_exc().splitlines()[-10:]})
    return JSONResponse(status_code=500, content={"error": "Internal Server Error"})


@app.get("/health")
def health():
    return {"ok": True, "use_stubs": config.USE_STUBS,
            "db_wired": config.DB_WIRED, "apply_live": config.APPLY_LIVE,
            "query_live": config.QUERY_LIVE,
            "handelsregister_backend": config.HANDELSREGISTER_BACKEND}


@app.post("/thesis", response_model=ThesisOut)
def save_thesis(body: ThesisIn):
    if not config.DB_WIRED:
        return ThesisOut(thesis_id=str(uuid.uuid4()))
    from db import upsert_thesis
    return upsert_thesis(body)


@app.post("/apply", response_model=ApplyOut, status_code=202)
async def apply(background: BackgroundTasks,
                company_name: str = Form(...), deck_file: UploadFile = File(...),
                founder_name: str | None = Form(None)):
    if not config.APPLY_LIVE:
        return ApplyOut(opportunity_id="e0000000-0000-0000-0000-000000000002")
    # Create the opportunity shell synchronously (fast) so we can return an id + 202 now,
    # then run the multi-agent pipeline in the background. The frontend polls
    # GET /opportunities/:id until decision.recommendation is set. This keeps the request
    # short so the Lovable proxy never times out on the 30-60s pipeline.
    from pipeline import create_opportunity, run_pipeline
    deck_bytes = await deck_file.read()
    opp_id = create_opportunity(company_name=company_name, founder_name=founder_name)
    background.add_task(run_pipeline, opportunity_id=opp_id, deck_bytes=deck_bytes)
    return ApplyOut(opportunity_id=opp_id)


@app.get("/opportunities", response_model=OpportunitiesOut)
def list_opportunities(stage: str | None = None, thesis_id: str | None = None):
    if not config.DB_WIRED:
        return stub_data.STUB_OPPORTUNITIES
    from db import get_opportunities
    return get_opportunities(stage=stage, thesis_id=thesis_id)


@app.get("/opportunities/{opportunity_id}", response_model=OpportunityDetail)
def get_opportunity(opportunity_id: str):
    if not config.DB_WIRED:
        return stub_data.STUB_DETAIL
    from db import get_opportunity_detail
    detail = get_opportunity_detail(opportunity_id)
    if not detail:
        raise HTTPException(404, "opportunity not found")
    return detail


@app.post("/query", response_model=QueryOut)
def query(body: QueryIn):
    if not config.QUERY_LIVE:
        return stub_data.STUB_QUERY
    from agents.query import run_query
    return run_query(body.q)


@app.post("/scan", response_model=ScanOut, status_code=202)
def scan(body: ScanIn | None = None):
    channels = (body.channels if body else None) or ["handelsregister"]
    if not config.DB_WIRED:
        return ScanOut(scan_id=str(uuid.uuid4()), channels=channels)
    from sourcing import run_scan
    scan_id = run_scan(channels)
    return ScanOut(scan_id=scan_id, channels=channels)


@app.get("/reasoning-log/{reasoning_log_id}", response_model=ReasoningLogOut)
def get_reasoning_log(reasoning_log_id: str):
    """Agentic Traceability: the step-level chain-of-thought behind an opportunity's memo."""
    if not config.DB_WIRED:
        return stub_data.STUB_REASONING_LOG
    from db import get_reasoning_log as fetch
    log = fetch(reasoning_log_id)
    if not log:
        raise HTTPException(404, "reasoning log not found")
    return log


@app.get("/founders/{founder_id}", response_model=FounderOut)
def get_founder(founder_id: str):
    if not config.DB_WIRED:
        return stub_data.STUB_FOUNDER
    from db import get_founder_profile
    profile = get_founder_profile(founder_id)
    if not profile:
        raise HTTPException(404, "founder not found")
    return profile
