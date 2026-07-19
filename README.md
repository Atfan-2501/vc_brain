# VC Brain

Two stacks. This repo is the **agent service** (the brain). The frontend lives in Lovable
(React + Supabase) and is edited there, not here. The two meet only at the REST contract
in `docs/api_contract.md`.

## What runs where
- **agent-service/** — FastAPI. Holds OpenAI + Tavily keys. Exposes the 7 contract endpoints.
- **Supabase** — Postgres = the Memory layer. Run `db/schema.sql` then `db/seed.sql`.
- **Lovable app** — calls this service at `AGENT_SERVICE_URL`. Renders only; no AI logic.

## Quickstart
```bash
cp .env.example .env            # fill in keys
cd agent-service
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
# open http://localhost:8000/docs  -> all 7 endpoints return contract-shaped STUB data
```

## Build order (see docs/runsheet.md)
1. H0–1: run schema+seed, deploy this service stubbed, point Lovable at it. Prove integration.
2. H1–6: fill `agents/*.py` in pipeline order. Flip `USE_STUBS=false` in `.env` per agent as it goes live.
3. Then sourcing, trust surface, UX.

Every endpoint returns fake-but-valid JSON until you wire the real agent. Never debug
integration and AI logic at the same time.
