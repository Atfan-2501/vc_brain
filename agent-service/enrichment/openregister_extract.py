"""Tier-0 enrichment: extract claims from the OpenRegister data we ALREADY fetched.
Zero new API cost — this reads the fields the detail call returned (financials, website,
social handles) and turns them into evidence-backed claims + founder handles.

Official-register financials get a HIGH trust score (independent, authoritative source),
unlike deck claims which stay unverified. This is the honest-provenance story in action."""
from __future__ import annotations


def claims_from_record(rec: dict) -> list[dict]:
    """rec = a HandelsregisterRecord as a dict (what's stored in signal.raw_content).
    Returns claim rows (company-level). Only emits claims for data that actually exists."""
    claims: list[dict] = []
    src = {"type": "web", "url": rec.get("source_url"),
           "citation": f"Handelsregister {rec.get('register_court','')} "
                       f"{rec.get('register_type','')} {rec.get('register_number','')}".strip()}

    def add(text, ctype, trust):
        claims.append({"claim_text": text, "claim_type": ctype,
                       "trust_score": trust, "verification_status": "verified",
                       "verification_evidence_url": rec.get("source_url"), "source_ref": src})

    if rec.get("revenue_eur") is not None:
        add(f"Reported revenue €{rec['revenue_eur']:,.0f} (official filing)", "financial", 0.9)
    if rec.get("net_income_eur") is not None:
        add(f"Reported net income €{rec['net_income_eur']:,.0f} (official filing)", "financial", 0.9)
    if rec.get("employees") is not None:
        add(f"{rec['employees']} employees (official filing)", "team", 0.85)
    if rec.get("business_purpose"):
        add(f"Registered business purpose: {rec['business_purpose']}", "market", 0.95)
    if rec.get("registered_on"):
        add(f"Incorporated {rec['registered_on']} (Handelsregister)", "team", 0.95)
    if rec.get("website"):
        add(f"Company website: {rec['website']}", "other", 0.9)
    return claims


def founder_handles_from_record(rec: dict) -> dict:
    """Social handles the register/website exposed — high-confidence seeds for Tier-1 GitHub
    and footprint resolution (no name-collision guessing needed when we have the real handle)."""
    return {
        "github_handle": rec.get("github_handle"),
        "linkedin_url": rec.get("linkedin_url"),
        "twitter_handle": rec.get("twitter_handle"),
        "website": rec.get("website"),
    }


def missing_data(rec: dict) -> list[str]:
    """Explicit gap flags — what a VC expects that the register does NOT provide. A memo that
    marks its own gaps scores as more trustworthy."""
    gaps = []
    if rec.get("revenue_eur") is None:
        gaps.append("Revenue: not in public filings")
    if not rec.get("managing_directors"):
        gaps.append("Founders/directors: not resolved from register")
    gaps.append("Cap table: not disclosed")
    gaps.append("Funding history: not disclosed")
    return gaps
