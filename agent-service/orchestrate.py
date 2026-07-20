"""Run the reasoning pipeline on a USER-SELECTED set of opportunities. Backs the board's
'Run pipeline on selected' action: enrich -> score -> memo, per chosen company, in order.
Each step is gated by its flag so partial setups degrade gracefully instead of erroring."""
from __future__ import annotations

import sys
import traceback

import config
import db


def _log(msg):
    print(f"[pipeline] {msg}", file=sys.stderr, flush=True)


def run_selected(opportunity_ids: list[str], steps: list[str]) -> dict:
    from enrichment.enrich import enrich_one
    from scoring import score_opportunity
    from memo_build import build_memo

    _log(f"start · {len(opportunity_ids)} opportunities · steps={steps} "
         f"· SCORING_LIVE={config.SCORING_LIVE} MEMO_LIVE={config.MEMO_LIVE} "
         f"WEB_ENRICH={config.WEB_ENRICH} SCREEN_GATES={config.SCREEN_GATES}")
    results = []
    for oid in opportunity_ids:
        core = db.get_opportunity_core(oid)
        if not core:
            _log(f"{oid} · NOT FOUND")
            results.append({"opportunity_id": oid, "error": "not found"})
            continue
        r = {"opportunity_id": oid}
        try:
            if "enrich" in steps and core.get("founder_id"):
                _log(f"{oid} · enriching…")
                enrich_one(core["founder_id"])
                r["enriched"] = True
            if "score" in steps and config.SCORING_LIVE:
                _log(f"{oid} · scoring…")
                res = score_opportunity(oid)
                r["scored"] = True
                r["screened_out"] = bool(res.get("screened_out"))
                if r["screened_out"]:
                    _log(f"{oid} · SCREENED OUT (thesis_fit={res.get('thesis_fit')}) "
                         f"— no scores/memo. Set SCREEN_GATES=false to score anyway.")
            if "memo" in steps and config.MEMO_LIVE and not r.get("screened_out"):
                _log(f"{oid} · memo…")
                build_memo(oid)
                r["memo"] = True
            # auto-embed so Ask the Brain works without a separate manual /embed step
            try:
                from embeddings import embed_company
                if embed_company(core["company_id"]):
                    r["embedded"] = True
            except Exception as e:
                _log(f"{oid} · embed skipped: {e}")
            _log(f"{oid} · done {r}")
        except Exception as e:
            _log(f"{oid} · ERROR: {type(e).__name__}: {e}")
            traceback.print_exc()
            r["error"] = str(e)
        results.append(r)
    _log(f"finished · {results}")
    return {"processed": len(results), "results": results}
