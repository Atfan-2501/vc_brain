"""Tier-2 enrichment: Tavily web search for the parts the register can't give us —
founder footprint, company traction, and market/competitor context. Results are stored as
signals (nothing discarded) and turned into claims via the extraction agent.

Bounded: 3 searches per founder. Web claims are capped at moderate trust (0.75) — consistent
with public sources but not independently verified — so they never outrank official-register
facts. Runs only when WEB_ENRICH is on (costs Tavily + one OpenAI extraction call)."""
from __future__ import annotations

import json
import hashlib
from datetime import datetime, timezone

import config

WEB_TRUST_CAP = 0.75      # public-web evidence never reads as independently verified


def _tavily(query: str, max_results: int = 5) -> list[dict]:
    res = config.tavily_client().search(query=query, max_results=max_results,
                                        search_depth="advanced")
    return res.get("results", []) or []


def gather(founder_name: str, company_name: str, business_purpose: str = "",
           sector: str | None = None) -> dict[str, list[dict]]:
    """Three bounded searches. Returns {category: [tavily results]}. Errors degrade to []."""
    year = datetime.now().year
    topic = sector or (business_purpose[:60] if business_purpose else company_name)
    queries = {
        "founder": f"{founder_name} {company_name} founder background",
        "traction": f"{company_name} startup product launch users funding {year}",
        "market": f"{topic} market size competitors {year}",
    }
    out: dict[str, list[dict]] = {}
    for cat, q in queries.items():
        try:
            out[cat] = _tavily(q)
        except Exception:
            out[cat] = []
    return out


def to_signals(founder_id, company_id, results: dict[str, list[dict]]) -> list[dict]:
    signals = []
    for cat, items in results.items():
        for r in items:
            url = r.get("url", "")
            if not url:
                continue
            signals.append({
                "founder_id": founder_id, "company_id": company_id,
                "source": "web", "source_url": url,
                "raw_content": (r.get("content") or "")[:4000],
                "tags": ["enrichment", "web", cat],
                "dedup_hash": "web:" + hashlib.sha256(url.encode()).hexdigest()[:24],
                "extracted_at": datetime.now(timezone.utc).isoformat(),
            })
    return signals


def _combined_text(results: dict[str, list[dict]]) -> str:
    parts = []
    for cat, items in results.items():
        for r in items:
            parts.append(f"[{cat}] SOURCE: {r.get('url','')}\n{(r.get('content') or '')[:1500]}")
    return "\n\n".join(parts)


def claims_from_web(results: dict[str, list[dict]]) -> list[dict]:
    """One extraction call over all gathered web text -> claim rows (trust-capped, unverified)."""
    text = _combined_text(results)
    if not text.strip():
        return []
    from agents.extraction import extract_claims_from_text
    extracted = extract_claims_from_text(text)
    claims = []
    for c in extracted.get("claims", []):
        conf = c.get("confidence", 0.5) or 0.5
        claims.append({
            "claim_text": c["claim_text"], "claim_type": c.get("claim_type", "other"),
            "trust_score": round(min(WEB_TRUST_CAP, conf * WEB_TRUST_CAP), 2),
            "verification_status": "unverified",
            "verification_evidence_url": (c.get("source_ref") or {}).get("url"),
            "source_ref": c.get("source_ref") or {"type": "web"},
        })
    return claims


def enrich_web(founder_id, company_id, founder_name, company_name,
               business_purpose="", sector=None) -> dict:
    """Full Tier-2 pass: gather -> signals + claims. Returns both (caller persists)."""
    results = gather(founder_name, company_name, business_purpose, sector)
    return {"signals": to_signals(founder_id, company_id, results),
            "claims": claims_from_web(results),
            "result_count": sum(len(v) for v in results.values())}
