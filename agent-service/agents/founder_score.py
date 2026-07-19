"""Founder Score Updater — persistent, per person, never resets. H6-H9.
Recompute from the founder's full signal history; append to founder_score_history.
Cold-start: wide interval, is_pre_track_record=true, lean on footprint + deck specificity."""
from schemas import FOUNDER_SCORE_SCHEMA
from ._common import call_structured


def recompute(signals: list[dict], deck_claims: list[dict] | None = None) -> dict:
    """Returns {founder_score, founder_score_interval, is_pre_track_record, drivers,
    cited_signal_ids, rationale}."""
    sig_str = "\n".join(f"[{s['signal_id']}] {s['source']}: {s.get('raw_content','')}"
                        for s in signals)
    cold = len(signals) <= 1  # heuristic; the model confirms via is_pre_track_record
    prompt = (f"Founder signals:\n{sig_str}\n\n"
              f"Deck claims (if any): {deck_claims}\n\n"
              "Compute a 0-100 Founder Score PLUS an uncertainty interval. "
              "Inputs: shipped work, execution velocity, recognition, prior outcomes, "
              "public-footprint quality, verified background. "
              + ("COLD-START: little/no track record — score on deck specificity/insight "
                 "density and public footprint; use a WIDE interval; set is_pre_track_record=true."
                 if cold else "Track record present — narrow the interval as evidence accrues."))
    return call_structured("founder_score", FOUNDER_SCORE_SCHEMA, prompt)
