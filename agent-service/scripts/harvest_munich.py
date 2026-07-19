"""One-time harvester: pull REAL Munich GmbHs from OpenRegister into the fixture file.

Why: the OpenRegister free tier is 50 credits/month (search=10, each detail=10). You do NOT
want to spend credits on every scan or live on stage. Run this ONCE locally to cache real data
into connectors/fixtures/munich_gmbh.json, commit it, then keep HANDELSREGISTER_BACKEND=fixture.
The demo then runs on real-but-cached data with zero live API calls.

Usage (from agent-service/):
    OPENREGISTER_API_KEY=or_xxx  OPENREGISTER_MAX_DETAILS=4  python scripts/harvest_munich.py

Get a free key: https://openregister.de/keys
"""
import os
import sys
import json
from dataclasses import asdict
from pathlib import Path

# make the agent-service package importable when run as a script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ["HANDELSREGISTER_BACKEND"] = "openregister"

import config          # noqa: E402  (after env is set)
from connectors import handelsregister as hr   # noqa: E402

FIXTURE = Path(__file__).resolve().parent.parent / "connectors" / "fixtures" / "munich_gmbh.json"


def _company_id_from_url(url: str) -> str | None:
    if url and "/company/" in url:
        return url.rsplit("/company/", 1)[-1]
    return None


def main():
    if not config.OPENREGISTER_API_KEY:
        sys.exit("Set OPENREGISTER_API_KEY (free key at https://openregister.de/keys).")

    # load existing harvest so we ADD new companies instead of re-ingesting (and re-paying for) them
    existing = []
    if FIXTURE.exists():
        try:
            existing = json.loads(FIXTURE.read_text(encoding="utf-8"))
        except Exception:
            existing = []
    skip = {cid for cid in (_company_id_from_url(r.get("source_url", "")) for r in existing) if cid}
    seen_urls = {r.get("source_url") for r in existing}
    print(f"Existing fixture: {len(existing)} companies. Skipping those; harvesting up to "
          f"{config.OPENREGISTER_MAX_DETAILS} NEW (~{10 + config.OPENREGISTER_MAX_DETAILS * 10}+ "
          f"credits, plus 10/extra search page)...")

    records = hr.search_munich(skip_company_ids=skip)     # paginates, skips already-harvested
    new_rows = [asdict(r) for r in records if r.source_url not in seen_urls]
    if not new_rows:
        sys.exit("No NEW records returned. Try raising OPENREGISTER_MAX_PAGES, or you may have "
                 "exhausted the non-shell Munich results.")

    merged = existing + new_rows
    FIXTURE.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Added {len(new_rows)} NEW companies (total now {len(merged)}):")
    for r in records:
        if r.source_url in seen_urls:
            continue
        who = ", ".join(r.managing_directors) or "(directors not listed)"
        print(f"  {r.registered_on}  {r.company_name}  [{r.register_id}]  -> {who}")
    print("\nDone. Commit the updated fixture and keep HANDELSREGISTER_BACKEND=fixture for the demo.")


if __name__ == "__main__":
    main()
