"""Screener Agent — fast first-pass viability filter against the ACTIVE thesis.
Kills clearly non-viable before full analysis. H1-H6."""
from schemas import SCREENER_SCHEMA
from ._common import call_structured


def screen(claims: list[dict], thesis: dict) -> dict:
    """Returns {passes_screen, thesis_fit, kill_reasons, rationale, cited_claim_ids}."""
    claims_str = "\n".join(f"[{c['claim_id']}] {c['claim_text']}" for c in claims)
    prompt = (f"Active thesis: {thesis}\n\nClaims:\n{claims_str}\n\n"
              "Decide if this opportunity is worth full analysis under the thesis. "
              "Off-thesis or clearly non-viable -> passes_screen=false with kill_reasons.")
    return call_structured("screener", SCREENER_SCHEMA, prompt,
                           extra_system=f"Score strictly through this thesis: {thesis}")
