"""Inbound (Apply) pipeline: pitch deck + company name -> full memo + decision.
deck -> extract (multimodal) -> verify (catches contradictions) -> 3 axes -> memo -> decision.
Reuses the same scoring + memo modules as the outbound funnel, so both funnels converge."""
import uuid
from datetime import datetime, timezone

import config
import db
from agents import extraction, verification
from enrichment import footprint_score


def _now():
    return datetime.now(timezone.utc).isoformat()


def create_opportunity(company_name: str, founder_name: str | None) -> str:
    """Fast, synchronous: create founder + company + inbound opportunity so /apply can return an
    id + 202 immediately. The heavy deck processing runs in run_pipeline (background)."""
    founder_id = None
    if founder_name:
        founder_id = db.upsert_founder_by_name({"name": founder_name, "is_pre_track_record": True})
    company_id = db.insert_company({"name": company_name, "founder_id": founder_id,
                                    "geography": None, "stage": "pre-seed"})
    return db.create_opportunity(company_id=company_id, founder_id=founder_id,
                                 source="inbound", stage="screening", first_signal_at=_now())


def run_pipeline(opportunity_id: str, deck_bytes: bytes) -> str:
    core = db.get_opportunity_core(opportunity_id)
    if not core:
        return opportunity_id
    company_id = core["company_id"]
    founder_id = core.get("founder_id")

    # store the deck as a signal (provenance), then extract claims from the slides (multimodal)
    db.insert_signal({"founder_id": founder_id, "company_id": company_id, "source": "deck",
                      "source_url": None, "raw_content": "pitch deck upload",
                      "tags": ["inbound", "deck"], "dedup_hash": f"deck:{opportunity_id}",
                      "extracted_at": _now()})
    try:
        images = extraction.pdf_to_images(deck_bytes)
        extracted = extraction.extract_claims(deck_images=images)
    except Exception as e:
        db.log_reasoning(opportunity_id, "extraction", 1, "deck ingest failed",
                         {"error": str(e)}, config.OPENAI_MODEL)
        extracted = {"claims": [], "missing_data": []}
    for c in extracted.get("claims", []):
        db.insert_claim(company_id, {"claim_text": c["claim_text"],
                                     "claim_type": c.get("claim_type"),
                                     "source_ref": c.get("source_ref")})
    db.log_reasoning(opportunity_id, "extraction", 1, "deck -> claims",
                     extracted, config.OPENAI_MODEL)

    # verify each claim against the web -> trust scores + contradiction catch (best-effort)
    for claim in db.claims_for_company(company_id):
        try:
            v = verification.verify_claim(claim)
            db.update_claim_verification(claim["claim_id"], v["trust_score"],
                                         v["verification_status"],
                                         v.get("verification_evidence_url"),
                                         v.get("contradiction_note"))
            db.log_reasoning(opportunity_id, "verification", 2, claim["claim_text"],
                             v, config.OPENAI_MODEL)
        except Exception:
            pass                                   # missing Tavily etc. -> claim stays unverified

    # fresh applicant Founder Score: cold-start prior (narrows later via enrichment)
    if founder_id:
        s = footprint_score.compute({}, None)
        db.append_founder_score(founder_id, s["score"], s["interval"])
        db.set_pre_track_record(founder_id, s["is_pre_track_record"])

    # reuse the SAME reasoning as outbound: 3 independent axes, then memo + decision
    from scoring import score_opportunity
    from memo_build import build_memo
    score_opportunity(opportunity_id)
    build_memo(opportunity_id)
    return opportunity_id
