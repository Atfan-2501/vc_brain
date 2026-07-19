"""Pipeline orchestrator — the vertical slice. H1-H6 gate lives here.
apply -> extract -> verify -> screen -> 3-axis -> memo -> decision, all logged.
Fill the DB writes as you go; keep each stage independently testable."""
import uuid
from datetime import datetime, timezone

import db
from agents import extraction, verification, screener, axis_scorer, memo, founder_score


def create_opportunity(company_name: str, founder_name: str | None) -> str:
    """Fast, synchronous: create the company + opportunity shell, stamp first_signal_at,
    return the id so /apply can respond 202 immediately. Heavy work runs in run_pipeline."""
    opp_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    company_id = _create_company(company_name, founder_name)
    _create_opportunity(opp_id, company_id, first_signal_at=now)
    return opp_id


def run_pipeline(opportunity_id: str, deck_bytes: bytes) -> str:
    """Runs the full funnel in the BACKGROUND after /apply has returned. The frontend polls
    GET /opportunities/:id until decision.recommendation is set."""
    opp_id = opportunity_id
    thesis = _active_thesis()
    company_id = _company_for_opportunity(opp_id)

    # 2. extract claims from the deck
    images = extraction.pdf_to_images(deck_bytes)
    extracted = extraction.extract_claims(deck_images=images)
    claim_ids = [db.insert_claim(company_id, _claim_row(c)) for c in extracted["claims"]]
    claims = _load_claims(claim_ids)
    db.log_reasoning(opp_id, "extraction", 1, "deck->claims", extracted, "gpt-4o")

    # 3. verify each claim -> trust scores + contradictions
    for c in claims:
        v = verification.verify_claim(c)
        db.update_claim_verification(c["claim_id"], v["trust_score"],
                                     v["verification_status"],
                                     v["verification_evidence_url"], v["contradiction_note"])
        db.log_reasoning(opp_id, "verification", 2, c["claim_text"], v, "gpt-4o")
    claims = _load_claims(claim_ids)  # reload with trust scores

    # 4. screen against thesis
    scr = screener.screen(claims, thesis)
    db.log_reasoning(opp_id, "screener", 3, "screen", scr, "gpt-4o")

    # 5. founder score (persistent) then 3 independent axes
    fscore = founder_score.recompute(signals=_founder_signals(company_id), deck_claims=claims)
    axes = axis_scorer.score_all_axes(claims, thesis, fscore)
    db.log_reasoning(opp_id, "axis_scorer", 4, "3 axes", axes, "gpt-4o")

    # 6. memo + decision
    m = memo.build_memo(claims, axes, fscore, thesis)
    db.log_reasoning(opp_id, "memo", 5, "memo+decision", m, "gpt-4o")

    # 7. persist everything, stamp decided_at
    db.update_opportunity(opp_id, _opportunity_fields(axes, m, decided_at=_now()))
    return opp_id


# ---------- small helpers (TODO: implement against db.py) ----------
def _now():
    return datetime.now(timezone.utc).isoformat()

def _active_thesis() -> dict:
    raise NotImplementedError("fetch the single active thesis via db")

def _create_company(name, founder_name) -> str:
    raise NotImplementedError

def _create_opportunity(opp_id, company_id, first_signal_at):
    raise NotImplementedError

def _company_for_opportunity(opp_id) -> str:
    raise NotImplementedError

def _claim_row(c: dict) -> dict:
    return {"claim_text": c["claim_text"], "claim_type": c["claim_type"],
            "source_ref": c["source_ref"]}

def _load_claims(claim_ids) -> list[dict]:
    raise NotImplementedError

def _founder_signals(company_id) -> list[dict]:
    raise NotImplementedError

def _opportunity_fields(axes, m, decided_at) -> dict:
    """Map 3 axes + memo + decision into the opportunities columns. Never blend axes."""
    f, mk, i = axes["founder"], axes["market"], axes["idea_vs_market"]
    return {
        "founder_axis_score": f["score"], "founder_axis_trend": f["trend"],
        "founder_axis_rationale": f["rationale"], "founder_axis_claim_ids": f["cited_claim_ids"],
        "market_axis_score": mk["score"], "market_axis_trend": mk["trend"],
        "market_axis_verdict": mk["verdict"], "market_axis_rationale": mk["rationale"],
        "market_axis_swot": mk["swot"], "market_axis_claim_ids": mk["cited_claim_ids"],
        "idea_axis_score": i["score"], "idea_axis_trend": i["trend"],
        "idea_axis_rationale": i["rationale"], "idea_axis_claim_ids": i["cited_claim_ids"],
        "memo": m, "decision_recommendation": m["recommendation"],
        "decision_rationale": m["decision_rationale"],
        "most_decisive_missing_datum": m["most_decisive_missing_datum"],
        "stage": "decision", "decided_at": decided_at,
    }
