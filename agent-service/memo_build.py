"""Memo orchestration. Assembles the required 5-section investment memo + the decision from the
enriched claims, the three axis scores, and the Founder Score. Persists the memo, the decision,
stamps decided_at (feeds the signal->decision speed metric), and logs the call for traceability."""
from __future__ import annotations
from datetime import datetime, timezone

import config
import db
from agents import memo as memo_agent


def build_memo(opportunity_id: str, persist: bool = True) -> dict:
    core = db.get_opportunity_core(opportunity_id)
    if not core:
        return {"error": "opportunity not found"}

    thesis = db.get_active_thesis() or {}
    claims = db.claims_for_company(core["company_id"])
    founder_score = db.founder_score_for(core["founder_id"]) if core.get("founder_id") else None
    axes = db.get_opportunity_axes(opportunity_id)      # never averaged; passed as three inputs

    m = memo_agent.build_memo(claims, axes, founder_score, thesis)

    memo_json = {
        "company_snapshot": m["company_snapshot"],
        "investment_hypotheses": m["investment_hypotheses"],
        "swot": m["swot"],
        "problem_and_product": m["problem_and_product"],
        "traction_and_kpis": m["traction_and_kpis"],
        "optional_sections": m.get("optional_sections", {}),
        "gaps_flagged": m["gaps_flagged"],
    }

    if persist:
        db.update_opportunity(opportunity_id, {
            "memo": memo_json,
            "decision_recommendation": m["recommendation"],
            "decision_rationale": m["decision_rationale"],
            "most_decisive_missing_datum": m["most_decisive_missing_datum"],
            "stage": "decision",
            "decided_at": datetime.now(timezone.utc).isoformat(),
            "reasoning_log_id": opportunity_id,
        })
        db.log_reasoning(opportunity_id, "memo", 5, "memo + decision", m, config.OPENAI_MODEL)

    return {"opportunity_id": opportunity_id, "memo": memo_json,
            "decision": {"recommendation": m["recommendation"],
                         "rationale": m["decision_rationale"],
                         "most_decisive_missing_datum": m["most_decisive_missing_datum"]}}


def build_all(limit: int | None = None) -> dict:
    ids = db.opportunities_needing_memo(limit)
    out = []
    for oid in ids:
        try:
            r = build_memo(oid)
            out.append({"opportunity_id": oid,
                        "recommendation": r.get("decision", {}).get("recommendation")})
        except Exception as e:
            out.append({"opportunity_id": oid, "error": str(e)})
    return {"memos": len(out), "opportunities": out}
