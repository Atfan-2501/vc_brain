"""Axis scoring orchestration. Runs the THREE independent axes for an opportunity, persists
them separately (never averaged), logs each call for traceability, and advances the pipeline
stage. Consumes the enriched claims + the Founder Score produced by the enrichment layer."""
from __future__ import annotations

import config
import db
from agents import axis_scorer


def score_opportunity(opportunity_id: str, persist: bool = True) -> dict:
    core = db.get_opportunity_core(opportunity_id)
    if not core:
        return {"error": "opportunity not found"}

    thesis = db.get_active_thesis() or {}
    claims = db.claims_for_company(core["company_id"])
    founder_score = db.founder_score_for(core["founder_id"]) if core.get("founder_id") else None

    # three independent OpenAI calls (Founder / Market / Idea-vs-Market). Never combined.
    axes = axis_scorer.score_all_axes(claims, thesis, founder_score)

    if persist:
        db.update_opportunity(opportunity_id, _axis_fields(axes, reasoning_log_id=opportunity_id))
        for i, (name, ax) in enumerate(axes.items(), start=1):
            db.log_reasoning(opportunity_id, "axis_scorer", i, f"axis: {name}",
                             ax, config.OPENAI_MODEL)
    return {"opportunity_id": opportunity_id, "axes": axes}


def score_all_unscored(limit: int | None = None) -> dict:
    ids = db.opportunities_unscored(limit)
    out = []
    for oid in ids:
        try:
            r = score_opportunity(oid)
            a = r.get("axes", {})
            out.append({"opportunity_id": oid,
                        "founder": a.get("founder", {}).get("score"),
                        "market": a.get("market", {}).get("score"),
                        "idea_vs_market": a.get("idea_vs_market", {}).get("score")})
        except Exception as e:
            out.append({"opportunity_id": oid, "error": str(e)})
    return {"scored": len(out), "opportunities": out}


def _axis_fields(axes: dict, reasoning_log_id: str) -> dict:
    """Map the three axis results into their own columns. No blended number is ever written.
    Advances the opportunity to 'screening' now that it carries scores."""
    f, mk, i = axes["founder"], axes["market"], axes["idea_vs_market"]
    return {
        "founder_axis_score": f["score"], "founder_axis_trend": f["trend"],
        "founder_axis_rationale": f["rationale"], "founder_axis_claim_ids": f["cited_claim_ids"],
        "market_axis_score": mk["score"], "market_axis_trend": mk["trend"],
        "market_axis_verdict": mk["verdict"], "market_axis_rationale": mk["rationale"],
        "market_axis_swot": mk["swot"], "market_axis_claim_ids": mk["cited_claim_ids"],
        "idea_axis_score": i["score"], "idea_axis_trend": i["trend"],
        "idea_axis_rationale": i["rationale"], "idea_axis_claim_ids": i["cited_claim_ids"],
        "reasoning_log_id": reasoning_log_id, "stage": "screening",
    }
