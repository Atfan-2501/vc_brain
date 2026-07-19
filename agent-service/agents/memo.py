"""Memo Agent — assembles the memo (5 required sections) + decision. H1-H6.
Every sentence cites claim IDs; missing data goes in gaps_flagged, never fabricated.
Padding is penalized — as brief as clarity allows."""
from schemas import MEMO_SCHEMA
from ._common import call_structured


def build_memo(claims: list[dict], axes: dict[str, dict],
               founder_score: dict | None, thesis: dict) -> dict:
    """Returns memo fields + recommendation + decision_rationale + most_decisive_missing_datum."""
    claims_str = "\n".join(
        f"[{c['claim_id']}] {c['claim_text']} "
        f"(trust {c.get('trust_score')}, {c.get('verification_status')})" for c in claims)
    prompt = (f"Thesis: {thesis}\nFounder Score: {founder_score}\n"
              f"Axis results (do NOT average): {axes}\n\nClaims:\n{claims_str}\n\n"
              "Write the memo: company_snapshot, investment_hypotheses, swot, "
              "problem_and_product, traction_and_kpis. Cite claim IDs in cited_claim_ids. "
              "Put every expected-but-absent datum in gaps_flagged verbatim "
              "(e.g. 'Cap table: not disclosed'). Then give recommendation "
              "(Invest $100K / Decline / Request specific info), decision_rationale, and the "
              "single most_decisive_missing_datum that would most change the decision.")
    return call_structured("memo", MEMO_SCHEMA, prompt)
