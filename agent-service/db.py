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


def insert_signal(signal: dict) -> str | None:
    """Insert a signal; return signal_id, or None if the dedup_hash already exists.
    Dedup is how the same founder discovered via multiple sources doesn't double-count."""
    sb = supabase_client()
    existing = sb.table("signals").select("signal_id").eq(
        "dedup_hash", signal["dedup_hash"]).limit(1).execute().data
    if existing:
        return None
    return sb.table("signals").insert(signal).execute().data[0]["signal_id"]


def insert_company(company: dict) -> str:
    return supabase_client().table("companies").insert(company).execute().data[0]["company_id"]


def upsert_founder_by_name(founder: dict) -> str:
    """Identity resolution (name-based for now). If a founder with this name exists, reuse it
    so the Founder Score follows the person across sources/companies; else create.
    TODO H6-H9: strengthen with github_handle/linkedin_slug/domain matching, not just name."""
    sb = supabase_client()
    hit = sb.table("founders").select("founder_id").eq(
        "name", founder["name"]).limit(1).execute().data
    if hit:
        return hit[0]["founder_id"]
    return sb.table("founders").insert(founder).execute().data[0]["founder_id"]


def link_signal(signal_id, founder_id, company_id):
    supabase_client().table("signals").update(
        {"founder_id": founder_id, "company_id": company_id}).eq(
        "signal_id", signal_id).execute()


def create_outbound_opportunity(company_id, founder_id, first_signal_at) -> str:
    """Create an outbound opportunity at stage 'sourcing' so it lands on the board and can be
    scored by the same funnel as inbound. Axes stay null until the scorer runs."""
    row = supabase_client().table("opportunities").insert({
        "company_id": company_id, "founder_id": founder_id, "source": "outbound",
        "stage": "sourcing", "first_signal_at": first_signal_at,
    }).execute().data[0]
    return row["opportunity_id"]


def log_reasoning(opportunity_id, agent, step, prompt, response, model):
    supabase_client().table("reasoning_log").insert({
        "opportunity_id": opportunity_id, "agent": agent, "step": step,
        "prompt": prompt, "response": response, "model": model,
    }).execute()


def set_pre_track_record(founder_id, value: bool):
    supabase_client().table("founders").update(
        {"is_pre_track_record": value}).eq("founder_id", founder_id).execute()


def get_founder_min(founder_id) -> dict | None:
    hit = supabase_client().table("founders").select("founder_id, name").eq(
        "founder_id", founder_id).limit(1).execute().data
    return hit[0] if hit else None


def company_signal_for_founder(founder_id):
    """The handelsregister signal.raw_content + company_id for this founder (None,None if absent)."""
    s = supabase_client().table("signals").select("company_id, raw_content").eq(
        "founder_id", founder_id).eq("source", "handelsregister").limit(1).execute().data
    if not s:
        return None, None
    return s[0]["raw_content"], s[0]["company_id"]


def founders_to_enrich(limit=None) -> list[dict]:
    """Outbound founders discovered via handelsregister that have NOT been enriched yet
    (no github signal). Returns {founder_id, name, company_id, company_signal_raw}."""
    sb = supabase_client()
    hr = sb.table("signals").select(
        "founder_id, company_id, raw_content, founders(name)").eq(
        "source", "handelsregister").execute().data
    gh = sb.table("signals").select("founder_id").eq("source", "github").execute().data
    enriched = {g["founder_id"] for g in gh if g.get("founder_id")}
    out, seen = [], set()
    for s in hr:
        fid = s.get("founder_id")
        if not fid or fid in enriched or fid in seen:
            continue
        seen.add(fid)
        out.append({"founder_id": fid, "name": (s.get("founders") or {}).get("name", ""),
                    "company_id": s.get("company_id"), "company_signal_raw": s.get("raw_content")})
        if limit and len(out) >= limit:
            break
    return out


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
    # derive has_contradiction: company_ids that have >=1 contradicted claim
    contradicted = sb.table("claims").select("company_id").eq(
        "verification_status", "contradicted").execute().data
    flagged = {c["company_id"] for c in contradicted}
    return {"opportunities": [_row_to_card(r, flagged) for r in rows]}


def get_opportunity_detail(opportunity_id) -> dict | None:
    sb = supabase_client()
    rows = sb.table("opportunities").select(
        "*, companies(name), founders(name, founder_score, founder_score_interval, is_pre_track_record)"
    ).eq("opportunity_id", opportunity_id).limit(1).execute().data
    if not rows:
        return None
    r = rows[0]
    company = r.get("companies") or {}
    founder = r.get("founders") or {}
    claims = sb.table("claims").select("*").eq("company_id", r["company_id"]).execute().data
    contradictions = [
        {"claim_id": c["claim_id"], "note": c.get("contradiction_note"),
         "evidence_url": c.get("verification_evidence_url")}
        for c in claims if c.get("verification_status") == "contradicted"
    ]
    return {
        "opportunity_id": r["opportunity_id"],
        "company_name": company.get("name", ""),
        "founder": {
            "founder_id": r.get("founder_id"), "name": founder.get("name"),
            "founder_score": founder.get("founder_score"),
            "founder_score_interval": founder.get("founder_score_interval"),
            "is_pre_track_record": founder.get("is_pre_track_record", False),
        },
        "axes": {
            "founder": {"score": r.get("founder_axis_score"), "trend": r.get("founder_axis_trend"),
                        "rationale": r.get("founder_axis_rationale"),
                        "cited_claim_ids": r.get("founder_axis_claim_ids") or [], "swot": None},
            "market": {"score": r.get("market_axis_score"), "trend": r.get("market_axis_trend"),
                       "verdict": r.get("market_axis_verdict"),
                       "rationale": r.get("market_axis_rationale"),
                       "swot": r.get("market_axis_swot"),
                       "cited_claim_ids": r.get("market_axis_claim_ids") or []},
            "idea_vs_market": {"score": r.get("idea_axis_score"), "trend": r.get("idea_axis_trend"),
                               "rationale": r.get("idea_axis_rationale"),
                               "cited_claim_ids": r.get("idea_axis_claim_ids") or [], "swot": None},
        },
        "claims": [_claim_out(c) for c in claims],
        "memo": r.get("memo") or {},
        "contradictions": contradictions,
        "decision": {
            "recommendation": r.get("decision_recommendation"),
            "rationale": r.get("decision_rationale"),
            "most_decisive_missing_datum": r.get("most_decisive_missing_datum"),
        },
        "reasoning_log_id": r.get("reasoning_log_id") or r["opportunity_id"],
        "first_signal_at": r.get("first_signal_at"), "decided_at": r.get("decided_at"),
    }


def _claim_out(c: dict) -> dict:
    return {
        "claim_id": c["claim_id"], "claim_text": c["claim_text"], "claim_type": c.get("claim_type"),
        "trust_score": c.get("trust_score"),
        "verification_status": c.get("verification_status", "unverified"),
        "verification_evidence_url": c.get("verification_evidence_url"),
        "contradiction_note": c.get("contradiction_note"), "source_ref": c.get("source_ref"),
    }


def get_founder_profile(founder_id) -> dict | None:
    sb = supabase_client()
    hit = sb.table("founders").select("*").eq("founder_id", founder_id).limit(1).execute().data
    if not hit:
        return None
    f = hit[0]
    history = sb.table("founder_score_history").select("*").eq(
        "founder_id", founder_id).order("at").execute().data
    companies = sb.table("companies").select("company_id, name").eq(
        "founder_id", founder_id).execute().data
    signals = sb.table("signals").select("signal_id, source, source_url, ingested_at").eq(
        "founder_id", founder_id).order("ingested_at", desc=True).execute().data
    return {
        "founder_id": f["founder_id"], "name": f["name"],
        "founder_score": f.get("founder_score"),
        "founder_score_interval": f.get("founder_score_interval"),
        "is_pre_track_record": f.get("is_pre_track_record", False),
        "score_history": [{"score": h["score"], "interval": h.get("interval"),
                           "at": h.get("at"), "trigger_signal_id": h.get("trigger_signal_id")}
                          for h in history],
        "companies": [{"company_id": c["company_id"], "name": c["name"], "role": "Founder"}
                      for c in companies],
        "signals": [{"signal_id": s["signal_id"], "source": s["source"],
                     "source_url": s.get("source_url"), "at": s.get("ingested_at")}
                    for s in signals],
    }


# ---------- scoring reads ----------
def get_opportunity_core(opportunity_id) -> dict | None:
    hit = supabase_client().table("opportunities").select(
        "opportunity_id, company_id, founder_id, thesis_id, stage").eq(
        "opportunity_id", opportunity_id).limit(1).execute().data
    return hit[0] if hit else None


def get_active_thesis() -> dict | None:
    hit = supabase_client().table("theses").select("*").eq(
        "active", True).limit(1).execute().data
    return hit[0] if hit else None


def claims_for_company(company_id) -> list[dict]:
    return supabase_client().table("claims").select("*").eq(
        "company_id", company_id).execute().data


def founder_score_for(founder_id) -> dict | None:
    hit = supabase_client().table("founders").select(
        "name, founder_score, founder_score_interval, is_pre_track_record").eq(
        "founder_id", founder_id).limit(1).execute().data
    return hit[0] if hit else None


def opportunities_unscored(limit=None) -> list[str]:
    """Opportunity ids that have no founder-axis score yet (i.e. not yet run through scoring)."""
    q = supabase_client().table("opportunities").select("opportunity_id").is_(
        "founder_axis_score", "null")
    rows = q.execute().data
    ids = [r["opportunity_id"] for r in rows]
    return ids[:limit] if limit else ids


def get_reasoning_log(reasoning_log_id) -> dict | None:
    """The id passed is the opportunity_id (opportunities.reasoning_log_id == opportunity_id).
    Returns all logged steps for that opportunity, ordered."""
    sb = supabase_client()
    steps = sb.table("reasoning_log").select("*").eq(
        "opportunity_id", reasoning_log_id).order("step").execute().data
    if not steps:
        return None
    return {
        "reasoning_log_id": reasoning_log_id,
        "opportunity_id": reasoning_log_id,
        "steps": [{"agent": s["agent"], "step": s.get("step"), "prompt": s.get("prompt"),
                   "response": s.get("response"), "model": s.get("model"),
                   "created_at": s.get("created_at")} for s in steps],
    }


def _row_to_card(r: dict, flagged_company_ids: set | None = None) -> dict:
    flagged_company_ids = flagged_company_ids or set()
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
        # board-level flag so the UI shows the contradiction dot without fetching detail.
        "has_contradiction": r.get("company_id") in flagged_company_ids,
        "decision": r.get("decision_recommendation"),
        "first_signal_at": r.get("first_signal_at"), "decided_at": r.get("decided_at"),
    }
