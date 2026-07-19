"""Supabase read/write helpers. Thin wrappers over the client so agents/pipeline
never touch SQL directly. Fill these in during H1-H6 as each endpoint goes live.
Every function returns contract-shaped dicts (see contracts.py) or writes rows."""
from config import supabase_client
from contracts import ThesisOut


# ---------- writes ----------
def upsert_thesis(body) -> ThesisOut:
    sb = supabase_client()
    sb.table("theses").update({"active": False}).eq("active", True).execute()  # single active thesis
    row = sb.table("theses").insert({
        "sectors": body.sectors, "stages": body.stages, "geographies": body.geographies,
        "check_size_usd": body.check_size_usd, "ownership_target_pct": body.ownership_target_pct,
        "risk_appetite": body.risk_appetite, "active": True,
    }).execute().data[0]
    return ThesisOut(thesis_id=row["thesis_id"])


def insert_claim(company_id, claim: dict) -> str:
    sb = supabase_client()
    row = sb.table("claims").insert({"company_id": company_id, **claim}).execute().data[0]
    return row["claim_id"]


def update_claim_verification(claim_id, trust_score, status, evidence_url, note):
    supabase_client().table("claims").update({
        "trust_score": trust_score, "verification_status": status,
        "verification_evidence_url": evidence_url, "contradiction_note": note,
    }).eq("claim_id", claim_id).execute()


def update_opportunity(opportunity_id, fields: dict):
    supabase_client().table("opportunities").update(fields).eq(
        "opportunity_id", opportunity_id).execute()


def log_reasoning(opportunity_id, agent, step, prompt, response, model):
    supabase_client().table("reasoning_log").insert({
        "opportunity_id": opportunity_id, "agent": agent, "step": step,
        "prompt": prompt, "response": response, "model": model,
    }).execute()


def append_founder_score(founder_id, score, interval, trigger_signal_id=None):
    sb = supabase_client()
    sb.table("founders").update({
        "founder_score": score, "founder_score_interval": interval}).eq(
        "founder_id", founder_id).execute()
    sb.table("founder_score_history").insert({
        "founder_id": founder_id, "score": score, "interval": interval,
        "trigger_signal_id": trigger_signal_id}).execute()


# ---------- reads (shape to contracts.py; TODO join axes/claims/memo) ----------
def get_opportunities(stage=None, thesis_id=None) -> dict:
    sb = supabase_client()
    q = sb.table("opportunities").select("*, companies(name), founders(name, is_pre_track_record)")
    if stage:
        q = q.eq("stage", stage)
    rows = q.execute().data
    # TODO: map each row -> contracts.OpportunityCard (axes as 3 separate objects)
    return {"opportunities": [_row_to_card(r) for r in rows]}


def get_opportunity_detail(opportunity_id) -> dict | None:
    # TODO: fetch opportunity + claims + memo + reasoning_log_id, map to OpportunityDetail
    raise NotImplementedError("wire in H1-H6")


def get_founder_profile(founder_id) -> dict | None:
    # TODO: founder + score_history + companies + signals -> FounderOut
    raise NotImplementedError("wire in H6-H9")


def get_reasoning_log(reasoning_log_id) -> dict | None:
    # TODO: fetch reasoning_log rows for this id -> ReasoningLogOut (steps ordered by step)
    raise NotImplementedError("wire in H9-H11")


def _row_to_card(r: dict) -> dict:
    return {
        "opportunity_id": r["opportunity_id"],
        "company_name": (r.get("companies") or {}).get("name", ""),
        "founder_name": (r.get("founders") or {}).get("name"),
        "founder_id": r.get("founder_id"),
        "stage": r["stage"], "source": r["source"],
        "is_pre_track_record": (r.get("founders") or {}).get("is_pre_track_record", False),
        "axes": {
            "founder": {"score": r.get("founder_axis_score"), "trend": r.get("founder_axis_trend")},
            "market": {"score": r.get("market_axis_score"), "trend": r.get("market_axis_trend"),
                       "verdict": r.get("market_axis_verdict")},
            "idea_vs_market": {"score": r.get("idea_axis_score"), "trend": r.get("idea_axis_trend")},
        },
        # cheap board-level flag so the UI can show the contradiction dot without fetching detail.
        # TODO: compute via a claims exists-check (any claim with verification_status='contradicted').
        "has_contradiction": bool(r.get("has_contradiction", False)),
        "decision": r.get("decision_recommendation"),
        "first_signal_at": r.get("first_signal_at"), "decided_at": r.get("decided_at"),
    }
