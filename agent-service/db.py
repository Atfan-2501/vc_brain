"""Supabase read/write helpers. Thin wrappers over the client so agents/pipeline
never touch SQL directly. Fill these in during H1-H6 as each endpoint goes live.
Every function returns contract-shaped dicts (see contracts.py) or writes rows."""
from config import supabase_client
from contracts import ThesisOut


def _owner():
    """Current request's user id (from auth context). None in single-tenant/dev mode."""
    from auth import current_user_id
    return current_user_id()


def _own(q):
    """Filter a query builder to the current owner (no-op when owner is None)."""
    o = _owner()
    return q.eq("owner_id", o) if o else q


def _stamp(row: dict) -> dict:
    """Add owner_id to a row being inserted (only when we have an owner)."""
    o = _owner()
    if o:
        row = {**row, "owner_id": o}
    return row


# ---------- writes ----------
def upsert_thesis(body) -> ThesisOut:
    sb = supabase_client()
    _own(sb.table("theses").update({"active": False}).eq("active", True)).execute()
    row = sb.table("theses").insert(_stamp({
        "sectors": body.sectors, "stages": body.stages, "geographies": body.geographies,
        "check_size_usd": body.check_size_usd, "ownership_target_pct": body.ownership_target_pct,
        "risk_appetite": body.risk_appetite, "active": True,
    })).execute().data[0]
    return ThesisOut(thesis_id=row["thesis_id"])


def insert_claim(company_id, claim: dict) -> str:
    sb = supabase_client()
    row = sb.table("claims").insert(_stamp({"company_id": company_id, **claim})).execute().data[0]
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
    existing = _own(sb.table("signals").select("signal_id").eq(
        "dedup_hash", signal["dedup_hash"])).limit(1).execute().data
    if existing:
        return None
    return sb.table("signals").insert(_stamp(signal)).execute().data[0]["signal_id"]


def insert_company(company: dict) -> str:
    return supabase_client().table("companies").insert(
        _stamp(company)).execute().data[0]["company_id"]


def upsert_founder_by_name(founder: dict) -> str:
    """Identity resolution (name-based), scoped to the owner so users don't share founder records.
    If a founder with this name exists for this owner, reuse it; else create."""
    sb = supabase_client()
    hit = _own(sb.table("founders").select("founder_id").eq(
        "name", founder["name"])).limit(1).execute().data
    if hit:
        return hit[0]["founder_id"]
    return sb.table("founders").insert(_stamp(founder)).execute().data[0]["founder_id"]


def link_signal(signal_id, founder_id, company_id):
    supabase_client().table("signals").update(
        {"founder_id": founder_id, "company_id": company_id}).eq(
        "signal_id", signal_id).execute()


def create_opportunity(company_id, founder_id, source, stage, first_signal_at) -> str:
    """General opportunity creator (inbound or outbound)."""
    row = supabase_client().table("opportunities").insert(_stamp({
        "company_id": company_id, "founder_id": founder_id, "source": source,
        "stage": stage, "first_signal_at": first_signal_at,
    })).execute().data[0]
    return row["opportunity_id"]


def create_outbound_opportunity(company_id, founder_id, first_signal_at) -> str:
    """Create an outbound opportunity at stage 'sourcing' so it lands on the board and can be
    scored by the same funnel as inbound. Axes stay null until the scorer runs."""
    row = supabase_client().table("opportunities").insert(_stamp({
        "company_id": company_id, "founder_id": founder_id, "source": "outbound",
        "stage": "sourcing", "first_signal_at": first_signal_at,
    })).execute().data[0]
    return row["opportunity_id"]


def log_reasoning(opportunity_id, agent, step, prompt, response, model):
    supabase_client().table("reasoning_log").insert(_stamp({
        "opportunity_id": opportunity_id, "agent": agent, "step": step,
        "prompt": prompt, "response": response, "model": model,
    })).execute()


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
    hr = _own(sb.table("signals").select(
        "founder_id, company_id, raw_content, founders(name)").eq(
        "source", "handelsregister")).execute().data
    gh = _own(sb.table("signals").select("founder_id").eq("source", "github")).execute().data
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
    q = _own(q)
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
        "thesis_fit": r.get("thesis_fit"),
        "passed_screen": r.get("passed_screen"),
        "screen_rationale": r.get("screen_rationale"),
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


# ---------- embeddings (semantic ranking for Ask the Brain) ----------
def companies_needing_embedding(limit=None, force=False) -> list[str]:
    """Company ids to embed. force=True re-embeds ALL (use after enrichment adds founder claims);
    otherwise only companies without an embedding yet."""
    q = _own(supabase_client().table("companies").select("company_id"))
    if not force:
        q = q.is_("embedding", "null")
    ids = [r["company_id"] for r in q.execute().data]
    return ids[:limit] if limit else ids


def build_company_doc(company_id) -> str:
    """COMPREHENSIVE knowledge document for a company — everything Memory knows about it, so
    RAG retrieval matches on substance: company + business purpose + founder (name, score,
    pre-track-record) + ALL claims (financials, GitHub footprint, web traction, team) + the
    axis rationales once scored. This rich doc is what makes semantic search actually effective."""
    import json
    sb = supabase_client()
    c = sb.table("companies").select("name, sector, geography, founder_id").eq(
        "company_id", company_id).limit(1).execute().data
    c = c[0] if c else {}

    purpose = ""
    sig = sb.table("signals").select("raw_content").eq(
        "company_id", company_id).eq("source", "handelsregister").limit(1).execute().data
    if sig:
        try:
            purpose = (json.loads(sig[0]["raw_content"]) or {}).get("business_purpose", "")
        except Exception:
            pass

    founder_line = ""
    if c.get("founder_id"):
        f = sb.table("founders").select(
            "name, founder_score, is_pre_track_record").eq(
            "founder_id", c["founder_id"]).limit(1).execute().data
        if f:
            f = f[0]
            bits = [f.get("name", "")]
            if f.get("founder_score") is not None:
                bits.append(f"founder score {f['founder_score']:g}")
            if f.get("is_pre_track_record"):
                bits.append("pre-track-record")
            founder_line = "Founder: " + ", ".join(b for b in bits if b)

    # ALL claims (not a subset) — they carry the real signal
    claims = sb.table("claims").select("claim_text").eq(
        "company_id", company_id).execute().data
    claim_texts = [cl["claim_text"] for cl in claims if cl.get("claim_text")][:20]

    # axis rationales, if the opportunity has been scored
    axis_texts = []
    opp = sb.table("opportunities").select(
        "founder_axis_rationale, market_axis_rationale, idea_axis_rationale").eq(
        "company_id", company_id).limit(1).execute().data
    if opp:
        for k in ("founder_axis_rationale", "market_axis_rationale", "idea_axis_rationale"):
            if opp[0].get(k):
                axis_texts.append(opp[0][k])

    parts = [c.get("name", ""), c.get("sector") or "", c.get("geography") or "", purpose]
    if founder_line:
        parts.append(founder_line)
    parts.extend(claim_texts)
    parts.extend(axis_texts)
    return " | ".join(p for p in parts if p)


def set_company_embedding(company_id, embedding: list[float], doc: str = ""):
    supabase_client().table("companies").update(
        {"embedding": embedding, "embedding_doc": doc}).eq("company_id", company_id).execute()


def semantic_search(query_text: str, top_k: int = 15) -> list[dict]:
    """Pure RAG retrieval: embed the query, cosine-rank ALL embedded companies, return the top-K
    with their doc (for LLM re-ranking). No hard structured pre-filter that could zero results."""
    from embeddings import embed_text, cosine
    sb = supabase_client()
    rows = _own(sb.table("companies").select(
        "company_id, name, embedding, embedding_doc").not_.is_(
        "embedding", "null")).execute().data
    if not rows:
        return []
    qemb = embed_text(query_text)
    scored = []
    for r in rows:
        emb = r.get("embedding")
        if emb:
            scored.append((cosine(qemb, emb), r))
    scored.sort(key=lambda x: x[0], reverse=True)

    out = []
    for score, r in scored[:top_k]:
        opp = sb.table("opportunities").select(
            "opportunity_id, founders(name)").eq(
            "company_id", r["company_id"]).limit(1).execute().data
        opp = opp[0] if opp else {}
        out.append({"opportunity_id": opp.get("opportunity_id"),
                    "company_id": r["company_id"], "company_name": r.get("name", ""),
                    "founder_name": (opp.get("founders") or {}).get("name"),
                    "relevance": round(score, 3), "doc": r.get("embedding_doc", "")})
    return out


# ---------- Ask the Brain (multi-attribute query) ----------
def query_opportunities(filters: dict, query_text: str | None = None) -> list[dict]:
    """One-pass query over Memory. Opportunity-level filters (stage/source) hit the DB; the
    joined company/founder conditions are applied in-process (fine at demo scale). If query_text
    is given and companies have embeddings, results are ranked by semantic similarity. Returns
    [{opportunity_id, company_name, match_reason, relevance?}]."""
    sb = supabase_client()
    q = _own(sb.table("opportunities").select(
        "opportunity_id, source, stage, "
        "companies(name, sector, geography, embedding), "
        "founders(name, founder_score, is_pre_track_record)"))
    if filters.get("stage"):
        q = q.eq("stage", filters["stage"])
    if filters.get("source"):
        q = q.eq("source", filters["source"])
    rows = q.execute().data

    # embed the query once for semantic ranking (best-effort; skip if no key/embeddings)
    qemb = None
    if query_text:
        try:
            from embeddings import embed_text
            qemb = embed_text(query_text)
        except Exception:
            qemb = None

    out = []
    for r in rows:
        comp = r.get("companies") or {}
        fnd = r.get("founders") or {}
        reasons = []

        def _has(field):
            v = filters.get(field)
            return v is not None and v != ""

        if _has("sector"):
            if filters["sector"].lower() not in (comp.get("sector") or "").lower():
                continue
            reasons.append(f"sector {comp.get('sector')}")
        if _has("geography"):
            if filters["geography"].lower() not in (comp.get("geography") or "").lower():
                continue
            reasons.append(f"geo {comp.get('geography')}")
        if filters.get("min_founder_score") is not None:
            if (fnd.get("founder_score") or 0) < filters["min_founder_score"]:
                continue
            reasons.append(f"founder score ≥ {filters['min_founder_score']:g}")
        if filters.get("is_pre_track_record") is not None:
            if bool(fnd.get("is_pre_track_record")) != filters["is_pre_track_record"]:
                continue
            reasons.append("pre-track-record" if filters["is_pre_track_record"] else "has track record")
        if _has("keyword"):
            kw = filters["keyword"].lower()
            hay = f"{comp.get('name','')} {comp.get('sector','')}".lower()
            if kw not in hay:
                continue
            reasons.append(f"matches '{filters['keyword']}'")
        if filters.get("stage"):
            reasons.append(f"stage {filters['stage']}")
        if filters.get("source"):
            reasons.append(filters["source"])

        # semantic relevance (optional): cosine of query vs company embedding
        relevance = None
        if qemb and comp.get("embedding"):
            from embeddings import cosine
            relevance = round(cosine(qemb, comp["embedding"]), 3)

        out.append({"opportunity_id": r["opportunity_id"],
                    "company_name": comp.get("name", ""),
                    "founder_name": fnd.get("name"),
                    "match_reason": ", ".join(reasons) or "matches query",
                    "relevance": relevance})

    # rank by semantic relevance when available; keep structured-only order otherwise
    if qemb:
        out.sort(key=lambda x: (x["relevance"] is not None, x["relevance"] or 0), reverse=True)
    return out


# ---------- scoring reads ----------
def get_opportunity_core(opportunity_id) -> dict | None:
    hit = supabase_client().table("opportunities").select(
        "opportunity_id, company_id, founder_id, thesis_id, stage").eq(
        "opportunity_id", opportunity_id).limit(1).execute().data
    return hit[0] if hit else None


def get_active_thesis() -> dict | None:
    hit = _own(supabase_client().table("theses").select("*").eq(
        "active", True)).limit(1).execute().data
    return hit[0] if hit else None


def claims_for_company(company_id) -> list[dict]:
    return supabase_client().table("claims").select("*").eq(
        "company_id", company_id).execute().data


def founder_score_for(founder_id) -> dict | None:
    hit = supabase_client().table("founders").select(
        "name, founder_score, founder_score_interval, is_pre_track_record").eq(
        "founder_id", founder_id).limit(1).execute().data
    return hit[0] if hit else None


def get_opportunity_axes(opportunity_id) -> dict:
    """Reconstruct the three persisted axis results (for the Memo Agent input)."""
    r = supabase_client().table("opportunities").select("*").eq(
        "opportunity_id", opportunity_id).limit(1).execute().data
    r = r[0] if r else {}
    return {
        "founder": {"score": r.get("founder_axis_score"), "trend": r.get("founder_axis_trend"),
                    "rationale": r.get("founder_axis_rationale"),
                    "cited_claim_ids": r.get("founder_axis_claim_ids") or []},
        "market": {"score": r.get("market_axis_score"), "trend": r.get("market_axis_trend"),
                   "verdict": r.get("market_axis_verdict"), "rationale": r.get("market_axis_rationale"),
                   "swot": r.get("market_axis_swot"), "cited_claim_ids": r.get("market_axis_claim_ids") or []},
        "idea_vs_market": {"score": r.get("idea_axis_score"), "trend": r.get("idea_axis_trend"),
                           "rationale": r.get("idea_axis_rationale"),
                           "cited_claim_ids": r.get("idea_axis_claim_ids") or []},
    }


def opportunities_needing_memo(limit=None) -> list[str]:
    """Opportunities that are scored (have a founder-axis score) but have no decision yet."""
    rows = _own(supabase_client().table("opportunities").select(
        "opportunity_id, founder_axis_score, decision_recommendation")).execute().data
    ids = [r["opportunity_id"] for r in rows
           if r.get("founder_axis_score") is not None and not r.get("decision_recommendation")]
    return ids[:limit] if limit else ids


def opportunities_unscored(limit=None) -> list[str]:
    """Opportunity ids that have no founder-axis score yet (i.e. not yet run through scoring)."""
    q = _own(supabase_client().table("opportunities").select("opportunity_id").is_(
        "founder_axis_score", "null"))
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
        "thesis_fit": r.get("thesis_fit"),
        "decision": r.get("decision_recommendation"),
        "first_signal_at": r.get("first_signal_at"), "decided_at": r.get("decided_at"),
    }
