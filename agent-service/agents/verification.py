"""Verification Agent (Trust Score) — per claim, Tavily search -> trust + status.
H1-H6. This is where the seeded contradictions get caught. Do not inflate internal
claims (revenue, cap table) — leave them unverified at honest low-mid trust."""
import config
from schemas import VERIFICATION_SCHEMA
from ._common import call_structured


def verify_claim(claim: dict) -> dict:
    """claim: {claim_id, claim_text, claim_type, source_ref}. Returns verification dict."""
    evidence = _tavily_search(claim["claim_text"])
    prompt = (f"Claim: {claim['claim_text']}\nType: {claim.get('claim_type')}\n"
              f"Source: {claim.get('source_ref')}\n\nExternal search results:\n{evidence}\n\n"
              "Assign trust_score (0-1) using: 0.9+ independently verified; 0.6-0.9 consistent "
              "but not confirmed; 0.3-0.6 plausible/unverifiable; <0.3 contradicted/implausible. "
              "If the claim conflicts with the evidence (e.g. revenue predates launch), set status "
              "'contradicted' and write a contradiction_note. Internal claims with no external "
              "evidence stay 'unverified' — never inflate.")
    result = call_structured("verification", VERIFICATION_SCHEMA, prompt)
    result["claim_id"] = claim["claim_id"]  # ensure the id round-trips
    return result


def _tavily_search(query: str) -> str:
    """Return clean RAG-ready text from Tavily. Include current year for time-sensitive queries."""
    res = config.tavily_client().search(query=query, max_results=5,
                                        search_depth="advanced")
    return "\n".join(f"- {r['title']}: {r['content']} ({r['url']})"
                     for r in res.get("results", []))
