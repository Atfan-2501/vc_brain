"""Enrichment orchestrator. Per discovered founder/company, run the tiers cheapest-first,
write everything to Memory as signals + claims, then let the existing scoring agents consume it.

Tier 0: OpenRegister data we already have  -> claims + founder handles   (free)
Tier 1: GitHub footprint                    -> signal + technical claims  (free)
Tier 2: Tavily web footprint/traction/market (TODO)                       (cheap)
Tier 3: Founder Score + axis scoring on the assembled evidence (existing agents)

Runs OFFLINE/BATCH (like the harvest), never live on stage. Bounded + cached per founder."""
from __future__ import annotations
import json

import config
from enrichment import github as gh
from enrichment import openregister_extract as t0
from enrichment import footprint_score as fs


def _infer_sector(rec: dict) -> str | None:
    from connectors.handelsregister import infer_sector
    return infer_sector(rec.get("business_purpose"))


def enrich_founder(founder: dict, company_signal_raw: str, company_id: str,
                   founder_id: str, persist: bool = True) -> dict:
    """founder: {founder_id, name}. company_signal_raw: the handelsregister signal.raw_content.
    Runs Tier 0 + Tier 1, computes the cold-start Founder Score, persists everything.
    Returns a summary. When persist=True, writes claims + github signal + founder score."""
    rec = json.loads(company_signal_raw) if isinstance(company_signal_raw, str) else company_signal_raw
    result = {"founder_id": founder_id, "name": founder.get("name"),
              "claims": [], "github": None, "gaps": [], "founder_score": None}

    # --- Tier 0: free claims from register data we already paid for ---
    all_claims = t0.claims_from_record(rec)
    handles = t0.founder_handles_from_record(rec)
    result["gaps"] = t0.missing_data(rec)

    # --- Tier 1: GitHub footprint (use the known handle if the register gave us one) ---
    fp = gh.resolve(founder_name=founder["name"], known_handle=handles.get("github_handle"))
    if fp:
        result["github"] = fp.__dict__
        all_claims += _github_claims(fp)

    # --- Tier 2: Tavily web footprint / traction / market (gated; costs Tavily + OpenAI) ---
    web_signals = []
    if config.WEB_ENRICH:
        from enrichment import web
        w = web.enrich_web(founder_id, company_id, founder["name"], rec.get("company_name", ""),
                           rec.get("business_purpose", ""), _infer_sector(rec))
        all_claims += w["claims"]
        web_signals = w["signals"]
        result["web"] = {"results": w["result_count"], "claims": len(w["claims"])}

    result["claims"] = all_claims

    # --- Founder Score from the assembled footprint (cold-start, with honest interval) ---
    score = fs.compute(rec, fp.__dict__ if fp else None)
    result["founder_score"] = score

    if persist:
        import db
        for c in all_claims:
            db.insert_claim(company_id, c)
        if fp:
            db.insert_signal(gh.to_signal_row(founder_id, fp))
        for s in web_signals:
            db.insert_signal(s)                         # dedups on url hash
        db.append_founder_score(founder_id, score["score"], score["interval"])
        db.set_pre_track_record(founder_id, score["is_pre_track_record"])
    return result


def enrich_one(founder_id: str, persist: bool = True) -> dict:
    """Enrich a single founder by id (the live-demo trigger)."""
    import db
    f = db.get_founder_min(founder_id)
    if not f:
        return {"error": "founder not found"}
    raw, company_id = db.company_signal_for_founder(founder_id)
    if raw is None:
        return {"error": "no handelsregister signal for this founder"}
    return enrich_founder(f, raw, company_id, founder_id, persist=persist)


def _github_claims(fp) -> list[dict]:
    """Turn GitHub footprint into claims. Trust is capped by match_confidence so a name-only
    match never reads as a confident assertion."""
    src = {"type": "web", "url": fp.profile_url, "citation": f"GitHub @{fp.login}"}
    base = fp.match_confidence
    out = []

    def add(text, ctype, trust):
        out.append({"claim_text": text, "claim_type": ctype,
                    "trust_score": round(min(trust, base), 2),
                    "verification_status": "verified" if base >= 0.75 else "unverified",
                    "verification_evidence_url": fp.profile_url, "source_ref": src})

    add(f"GitHub @{fp.login}: {fp.public_repos} repos, {fp.total_stars} stars, "
        f"{fp.followers} followers", "team", 0.9)
    if fp.top_languages:
        add(f"Primary languages: {', '.join(fp.top_languages)}", "tech", 0.85)
    if fp.recent_push_days_ago is not None and fp.recent_push_days_ago <= 90:
        add(f"Actively shipping — last push {fp.recent_push_days_ago}d ago", "traction", 0.85)
    if fp.notable_repos and fp.notable_repos[0]["stars"] >= 50:
        r = fp.notable_repos[0]
        add(f"Notable repo {r['name']} ({r['stars']} stars)", "traction", 0.9)
    return out


def enrich_all(limit: int | None = None, persist: bool = True) -> dict:
    """Batch: enrich outbound (handelsregister) founders not yet enriched. Deliberate/triggered —
    not automatic on /scan — to keep API usage controllable. Skips already-enriched founders."""
    import db
    todo = db.founders_to_enrich(limit)
    summaries = []
    for f in todo:
        try:
            s = enrich_founder(f, f["company_signal_raw"], f["company_id"],
                               f["founder_id"], persist=persist)
            summaries.append({"founder_id": f["founder_id"], "name": f.get("name"),
                              "score": (s.get("founder_score") or {}).get("score"),
                              "interval": (s.get("founder_score") or {}).get("interval"),
                              "github": bool(s.get("github")), "claims": len(s.get("claims", []))})
        except Exception as e:
            summaries.append({"founder_id": f["founder_id"], "name": f.get("name"),
                              "error": str(e)})
    return {"enriched": len(summaries), "founders": summaries}
