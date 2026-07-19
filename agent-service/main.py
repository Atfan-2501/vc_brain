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
    QueryIn, QueryOut, ScanIn, ScanOut, FounderOut, ReasoningLogOut, PipelineIn,
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


@app.post("/embed", status_code=202)
def embed_backfill(background: BackgroundTasks, limit: int | None = None):
    """Backfill semantic embeddings for companies (needed for Ask-the-Brain relevance ranking).
    Deliberate/background so it doesn't silently spend OpenAI. Run once after a scan."""
    if not config.DB_WIRED:
        raise HTTPException(400, "DB_WIRED required")
    from embeddings import embed_all
    from contracts import now_iso
    background.add_task(embed_all, limit)
    return {"status": "embedding", "limit": limit, "generated_at": now_iso()}


@app.post("/pipeline", status_code=202)
def pipeline_selected(body: PipelineIn, background: BackgroundTasks):
    """Run the reasoning pipeline (enrich -> score -> memo) on a user-SELECTED set of
    opportunities from the board. Runs in the background; poll /opportunities to watch the
    selected cards move Sourcing -> Screening -> Decision with scores. Each stage is gated by
    its own flag, so unselected/unavailable steps are simply skipped."""
    if not config.DB_WIRED:
        raise HTTPException(400, "DB_WIRED required")
    from orchestrate import run_selected
    from contracts import now_iso
    background.add_task(run_selected, body.opportunity_ids, body.steps)
    return {"status": "processing", "count": len(body.opportunity_ids),
            "steps": body.steps, "generated_at": now_iso()}


@app.post("/memo/{opportunity_id}")
def memo_one_endpoint(opportunity_id: str):
    """Generate the 5-section investment memo + decision for one scored opportunity (OpenAI).
    Stamps decided_at (feeds the speed metric). The 'produce the memo now' demo action."""
    if not (config.DB_WIRED and config.MEMO_LIVE):
        raise HTTPException(400, "DB_WIRED and MEMO_LIVE required for memo generation")
    from memo_build import build_memo
    return build_memo(opportunity_id)


@app.post("/memo", status_code=202)
def memo_batch_endpoint(background: BackgroundTasks, limit: int | None = None):
    """Batch: write memos + decisions for every scored opportunity that has no decision yet."""
    if not (config.DB_WIRED and config.MEMO_LIVE):
        raise HTTPException(400, "DB_WIRED and MEMO_LIVE required for memo generation")
    from memo_build import build_all
    from contracts import now_iso
    background.add_task(build_all, limit)
    return {"status": "writing_memos", "limit": limit, "generated_at": now_iso()}


@app.post("/score/{opportunity_id}")
def score_one_endpoint(opportunity_id: str):
    """Run the 3 independent axes for one opportunity (OpenAI). The live-demo 'score this now'
    action — produces Founder/Market/Idea scores + Market SWOT, persisted separately."""
    if not (config.DB_WIRED and config.SCORING_LIVE):
        raise HTTPException(400, "DB_WIRED and SCORING_LIVE required for scoring")
    from scoring import score_opportunity
    return score_opportunity(opportunity_id)


@app.post("/score", status_code=202)
def score_batch_endpoint(background: BackgroundTasks, limit: int | None = None):
    """Batch-score every opportunity that has no axis scores yet. Runs in the background
    (3 OpenAI calls each); poll /opportunities to watch scores land on the board."""
    if not (config.DB_WIRED and config.SCORING_LIVE):
        raise HTTPException(400, "DB_WIRED and SCORING_LIVE required for scoring")
    from scoring import score_all_unscored
    from contracts import now_iso
    background.add_task(score_all_unscored, limit)
    return {"status": "scoring", "limit": limit, "generated_at": now_iso()}


@app.post("/enrich/{founder_id}")
def enrich_one_endpoint(founder_id: str):
    """Depth layer: enrich a single discovered founder (Tier 0 register data + Tier 1 GitHub),
    compute the cold-start Founder Score, persist. The live-demo 'enrich this founder now' action."""
    if not config.DB_WIRED:
        raise HTTPException(400, "DB_WIRED required for enrichment")
    from enrichment.enrich import enrich_one
    return enrich_one(founder_id)


@app.post("/enrich", status_code=202)
def enrich_batch_endpoint(background: BackgroundTasks, limit: int | None = None):
    """Batch-enrich discovered founders not yet enriched. Runs in the background (GitHub/network
    per founder); poll /founders/:id or /opportunities to see scores land."""
    if not config.DB_WIRED:
        raise HTTPException(400, "DB_WIRED required for enrichment")
    from enrichment.enrich import enrich_all
    background.add_task(enrich_all, limit)
    from contracts import now_iso
    return {"status": "enriching", "limit": limit, "generated_at": now_iso()}


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
