"""Run the reasoning pipeline on a USER-SELECTED set of opportunities. Backs the board's
'Run pipeline on selected' action: enrich -> score -> memo, per chosen company, in order.
Each step is gated by its flag so partial setups degrade gracefully instead of erroring."""
from __future__ import annotations

import config
import db


def run_selected(opportunity_ids: list[str], steps: list[str]) -> dict:
    from enrichment.enrich import enrich_one
    from scoring import score_opportunity
    from memo_build import build_memo

    results = []
    for oid in opportunity_ids:
        core = db.get_opportunity_core(oid)
        if not core:
            results.append({"opportunity_id": oid, "error": "not found"})
            continue
        r = {"opportunity_id": oid}
        try:
            if "enrich" in steps and core.get("founder_id"):
                enrich_one(core["founder_id"])
                r["enriched"] = True
            if "score" in steps and config.SCORING_LIVE:
                res = score_opportunity(oid)
                r["scored"] = True
                r["screened_out"] = bool(res.get("screened_out"))
            # skip the memo for off-thesis founders (screened out) — no point analyzing them
            if "memo" in steps and config.MEMO_LIVE and not r.get("screened_out"):
                build_memo(oid)
                r["memo"] = True
        except Exception as e:
            r["error"] = str(e)
        results.append(r)
    return {"processed": len(results), "results": results}
