"""Pydantic models mirroring docs/api_contract.md — the shapes sent TO the Lovable app.
Keep this in lockstep with the contract. These are NOT the OpenAI schemas (see schemas.py)."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional, Literal
from pydantic import BaseModel, Field


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


Trend = Literal["improving", "declining", "stable"]
Verdict = Literal["bullish", "neutral", "bear"]
Stage = Literal["sourcing", "screening", "diligence", "decision"]
Recommendation = Literal["Invest $100K", "Decline", "Request specific info"]


# ---------- thesis ----------
class ThesisIn(BaseModel):
    sectors: list[str] = []
    stages: list[str] = []
    geographies: list[str] = []
    check_size_usd: int = 100_000
    ownership_target_pct: Optional[float] = None
    risk_appetite: Optional[Literal["low", "medium", "high"]] = None


class ThesisOut(BaseModel):
    thesis_id: str
    active: bool = True
    generated_at: str = Field(default_factory=now_iso)


# ---------- apply ----------
class ApplyOut(BaseModel):
    opportunity_id: str
    status: str = "processing"
    first_signal_at: str = Field(default_factory=now_iso)
    generated_at: str = Field(default_factory=now_iso)


# ---------- axes ----------
class AxisBrief(BaseModel):
    score: Optional[int] = None
    trend: Optional[Trend] = None
    verdict: Optional[Verdict] = None


class AxisFull(AxisBrief):
    rationale: Optional[str] = None
    cited_claim_ids: list[str] = []
    swot: Optional[dict] = None


class OpportunityCard(BaseModel):
    opportunity_id: str
    company_name: str
    founder_name: Optional[str] = None
    founder_id: Optional[str] = None
    stage: Stage
    source: Literal["inbound", "outbound"]
    is_pre_track_record: bool = False
    axes: dict[str, AxisBrief]   # keys: founder, market, idea_vs_market
    has_contradiction: bool = False   # so the board can show the dot without fetching detail
    decision: Optional[str] = None
    first_signal_at: Optional[str] = None
    decided_at: Optional[str] = None


class OpportunitiesOut(BaseModel):
    opportunities: list[OpportunityCard]
    generated_at: str = Field(default_factory=now_iso)


# ---------- claims / memo / detail ----------
class Claim(BaseModel):
    claim_id: str
    claim_text: str
    claim_type: Optional[str] = None
    trust_score: Optional[float] = None
    verification_status: Literal["verified", "unverified", "contradicted"] = "unverified"
    verification_evidence_url: Optional[str] = None
    contradiction_note: Optional[str] = None
    source_ref: Optional[dict] = None


class Memo(BaseModel):
    company_snapshot: str = ""
    investment_hypotheses: list[str] = []
    swot: dict = {}
    problem_and_product: str = ""
    traction_and_kpis: str = ""
    optional_sections: dict = {}
    gaps_flagged: list[str] = []


class Decision(BaseModel):
    recommendation: Optional[Recommendation] = None
    rationale: Optional[str] = None
    most_decisive_missing_datum: Optional[str] = None


class FounderBrief(BaseModel):
    founder_id: Optional[str] = None
    name: Optional[str] = None
    founder_score: Optional[float] = None
    founder_score_interval: Optional[float] = None
    is_pre_track_record: bool = False


class OpportunityDetail(BaseModel):
    opportunity_id: str
    company_name: str
    founder: FounderBrief
    axes: dict[str, AxisFull]
    claims: list[Claim] = []
    memo: Memo
    contradictions: list[dict] = []
    decision: Decision
    reasoning_log_id: Optional[str] = None
    first_signal_at: Optional[str] = None
    decided_at: Optional[str] = None
    generated_at: str = Field(default_factory=now_iso)


# ---------- query ----------
class QueryIn(BaseModel):
    q: str


class QueryOut(BaseModel):
    parsed_filters: dict = {}
    results: list[dict] = []
    generated_at: str = Field(default_factory=now_iso)


# ---------- scan ----------
class ScanIn(BaseModel):
    channels: list[str] = ["handelsregister"]   # the built connector; add show_hn/producthunt later


class ScanOut(BaseModel):
    scan_id: str
    channels: list[str]
    status: str = "scanning"
    generated_at: str = Field(default_factory=now_iso)


# ---------- reasoning log (Agentic Traceability) ----------
class ReasoningStep(BaseModel):
    agent: str
    step: Optional[int] = None
    prompt: Optional[str] = None
    response: Optional[dict] = None
    model: Optional[str] = None
    created_at: Optional[str] = None


class ReasoningLogOut(BaseModel):
    reasoning_log_id: str
    opportunity_id: Optional[str] = None
    steps: list[ReasoningStep] = []
    generated_at: str = Field(default_factory=now_iso)


# ---------- founder ----------
class FounderOut(BaseModel):
    founder_id: str
    name: str
    founder_score: Optional[float] = None
    founder_score_interval: Optional[float] = None
    is_pre_track_record: bool = False
    score_history: list[dict] = []
    companies: list[dict] = []
    signals: list[dict] = []
    generated_at: str = Field(default_factory=now_iso)
