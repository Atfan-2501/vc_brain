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


def main():
    if not config.OPENREGISTER_API_KEY:
        sys.exit("Set OPENREGISTER_API_KEY (free key at https://openregister.de/keys).")

    print(f"Harvesting up to {config.OPENREGISTER_MAX_DETAILS} Munich GmbHs from OpenRegister "
          f"(~{10 + config.OPENREGISTER_MAX_DETAILS * 10} credits)...")
    records = hr.search_munich()          # openregister backend: search + detail
    if not records:
        sys.exit("No records returned. Check your key/credits or the search filters.")

    rows = [asdict(r) for r in records]
    FIXTURE.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(rows)} REAL companies to {FIXTURE.name}:")
    for r in records:
        who = ", ".join(r.managing_directors) or "(directors not listed)"
        print(f"  {r.registered_on}  {r.company_name}  [{r.register_id}]  -> {who}")
    print("\nDone. Commit the updated fixture and keep HANDELSREGISTER_BACKEND=fixture for the demo.")


if __name__ == "__main__":
    main()
