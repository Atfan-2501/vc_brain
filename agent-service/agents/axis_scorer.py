"""Axis Scorer — THREE INDEPENDENT calls. Never average them. H1-H6.
Market axis returns verdict + SWOT; the other two return null for those fields.
Each returns score, trend, rationale, cited_claim_ids -> Agentic Traceability."""
from schemas import AXIS_SCHEMA
from ._common import call_structured

AXES = ["founder", "market", "idea_vs_market"]

_AXIS_GUIDE = {
    "founder": "Who they are: traits, track record, team, red flags + why acceptable. "
               "Consume the provided Founder Score as ONE input, not a substitute.",
    "market": "Sizing (TAM/SAM/SOM with stated assumptions), competitor clusters, SWOT. "
              "Return verdict bullish/neutral/bear and a filled swot object.",
    "idea_vs_market": "Does the idea survive scrutiny as-is? If not, is the team strong "
                      "enough to pivot? Reason explicitly about idea-quality vs team-quality.",
}


def score_axis(axis: str, claims: list[dict], thesis: dict, founder_score: dict | None) -> dict:
    claims_str = "\n".join(f"[{c['claim_id']}] {c['claim_text']} "
                           f"(trust {c.get('trust_score')})" for c in claims)
    prompt = (f"Axis: {axis}\nGuidance: {_AXIS_GUIDE[axis]}\n\n"
              f"Founder Score input: {founder_score}\n\nClaims:\n{claims_str}\n\n"
              "Score 1-10, set trend, write a one-paragraph rationale citing claim IDs.")
    result = call_structured("axis_scorer", AXIS_SCHEMA, prompt,
                             extra_system=f"Thesis lens: {thesis}")
    result["axis"] = axis
    if axis != "market":                 # enforce: only market carries verdict+swot
        result["verdict"], result["swot"] = None, None
    return result


def score_all_axes(claims, thesis, founder_score) -> dict[str, dict]:
    """Returns {founder: {...}, market: {...}, idea_vs_market: {...}} — three separate results."""
    return {a: score_axis(a, claims, thesis, founder_score) for a in AXES}
