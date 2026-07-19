# The VC Brain

**An autonomous VC operating system that discovers exceptional founders before their first round, scores them through a configurable fund thesis, and produces an evidence-backed investment recommendation — in minutes, not weeks.**

Built for **Hack-Nation · Challenge 02 (Maschmeyer Group)**. Scope: **Sourcing → Screening → Diligence → Decision.**

Focus market for the live demo: **Munich** — using real German commercial-register data to surface founders *at the moment their company is formed*, before any funding, press, or network signal exists.

---

## The idea in one line

A founder — spotted via a fresh company registration or applying cold with a pitch deck — learns within a 24-hour window whether they fit the fund, based on a living, evidence-backed profile the system builds from public data. Merit, not network.

---

## What makes this different

Most "AI VC" tools are a thin reasoning layer over shallow data. We inverted that: **deep, honest sourcing first**, with a transparent intelligence layer on top.

- **Discovers founders before their first round.** The outbound scanner ingests newly-formed Munich GmbHs from the Handelsregister (via OpenRegister) — the earliest possible founder signal, before GitHub traction or funding exists.
- **Solves cold-start explicitly.** A first-time founder with no track record still gets a **Founder Score with an honest uncertainty interval** (e.g. `49 ± 32`), labelled *pre-track-record* — reasoned about, never penalized for silence. This directly operationalizes the challenge's open research question: *how much do public footprints predict founder success?*
- **Trust is per claim, not per company.** Every assertion carries a source and a trust score: official-register financials at `0.9`, a name-matched GitHub capped by match confidence, public-web evidence capped at `0.75`, pitch-deck claims treated as internal evidence. Nothing is inflated.
- **Never fabricates.** Missing data is flagged ("Cap table: not disclosed"), never invented — a memo that marks its own gaps is more trustworthy.
- **Catches contradictions before the investor sees them.** A deck claiming "$50K MRR" while launching three weeks ago gets flagged by the verification agent.
- **The three screening axes are never averaged.** Founder, Market, and Idea-vs-Market are independent scores, each with a trend and cited evidence — surfacing disagreement (Founder 9 / Market 3) is the point.

---

## Architecture

Two stacks that meet only at a frozen REST contract, plus a shared Memory layer.

```
        ┌────────────────────────┐        REST (server-proxied)      ┌──────────────────────────┐
        │   Experience (Lovable) │  ───────────────────────────────▶ │  Agent Service (FastAPI) │
        │  React · TanStack Query│                                   │        "the brain"       │
        │  pipeline board, memo, │  ◀─────────────────────────────── │  OpenAI · Tavily · GitHub│
        │  Ask the Brain, Apply  │                                   │  OpenRegister · PyMuPDF  │
        └────────────────────────┘                                   └────────────┬─────────────┘
                                                                                   │
                                                                    ┌──────────────▼─────────────┐
                                                                    │   Memory (Supabase / PG)   │
                                                                    │ founders · companies ·     │
                                                                    │ signals · claims ·         │
                                                                    │ opportunities · theses ·   │
                                                                    │ reasoning_log              │
                                                                    └────────────────────────────┘
```

**Three pillars** (matching the brief):
1. **Memory** — Postgres. Every raw signal, atomic claim, persistent Founder Score, and reasoning step. Nothing is discarded; trends over time are preserved.
2. **Assessment & Intelligence** — a chain of transparent agents (extraction, verification, screener, 3-axis scorer, Founder Score, memo), each an OpenAI structured-output call logged step-by-step.
3. **Experience** — an investor-grade UI: *Notion-level approachability, Bloomberg-level depth.*

---

## The two funnels converge

Both inbound and outbound flow through the **same** screening → scoring → memo code.

**Outbound (discover):**
```
/scan  →  Handelsregister (Munich GmbHs)  →  signals
       →  enrich: Tier 0 register data · Tier 1 GitHub footprint · Tier 2 web (Tavily)
       →  Founder Score (cold-start, uncertainty interval)
       →  thesis screen  →  3 independent axes  →  memo  →  decision
```

**Inbound (apply):**
```
/apply (pitch deck PDF + company name)
       →  PyMuPDF renders slides  →  multimodal claim extraction
       →  per-claim verification (contradiction catch)
       →  thesis screen  →  3 independent axes  →  memo  →  decision
```

---

## How each MVP requirement is met

| # | Requirement | Where it lives |
|---|-------------|----------------|
| 1 | **Thesis Engine** (configurable, not hardcoded) | `POST /thesis`; the active thesis gates the funnel via the Screener and tints every axis score |
| 2 | **Smart Data Collection** | OpenRegister harvest (Munich GmbHs, shell-company filtered), GitHub API, Tavily web; dedup + founder identity resolution across sources |
| 3 | **Multi-Attribute Reasoning** | `POST /query` — **RAG**: semantic retrieval over comprehensive per-company documents + LLM re-rank & synthesized answer |
| 4 | **Inbound Application & Automated Screening** | `POST /apply` (deck + company name) → extraction → verification → **Screener** gate |
| 5 | **Outbound Identification & Activation** | `POST /scan` → same funnel as inbound; both converge |
| 6 | **Multi-Axis Screening** | Founder / Market / Idea-vs-Market — three independent OpenAI calls, **never averaged**, each with trend + rationale + cited claim IDs; Market returns bullish/neutral/bear + SWOT |
| 7 | **Evidence-Backed Memos & Trust Score** | Memo Agent → 5 required sections, claims cited, gaps flagged; per-claim trust + verification status + contradiction notes |
| 8 | **Investor-Grade UX** | Lovable app: pipeline board with side-by-side axis scores, evidence chips, contradiction dots, Founder Score sparkline, Ask the Brain |

**Founder Score ≠ 3-axis score.** The Founder Score is persistent, attached to the *person*, follows them across companies, and never resets — it's one *input* to the Founder axis, not a replacement.

---

## Stretch goals

- **Agentic Traceability** — every agent call is written to `reasoning_log`; every score cites the claim IDs it rests on; the memo footer deep-links to the full chain-of-thought (`GET /reasoning-log/:id`).
- **Self-correction** — the verification agent cross-references extracted claims against the web and flags contradictions before they reach the memo.

---

## Tech stack

- **Agent service:** Python · FastAPI · deployed on Render
- **Reasoning:** OpenAI (`gpt-4o` structured outputs · `text-embedding-3-small` for RAG)
- **External data:** OpenRegister (Handelsregister) · GitHub REST API · Tavily (search-for-agents)
- **Deck ingestion:** PyMuPDF (multimodal)
- **Memory:** Supabase (Postgres)
- **Frontend:** Lovable (React · TanStack Query · server-proxied so keys stay server-side)

---

## Repository layout

```
vc-brain/
├── agent-service/          # FastAPI "brain"
│   ├── main.py             # the REST endpoints (thin orchestration)
│   ├── agents/             # extraction · verification · screener · axis_scorer · memo · query
│   ├── enrichment/         # Tier 0 register · Tier 1 GitHub · Tier 2 web · Founder Score · orchestrator
│   ├── connectors/         # Handelsregister / OpenRegister connector (+ Munich fixture)
│   ├── scoring.py          # 3-axis scoring + thesis screen gate
│   ├── memo_build.py       # memo + decision
│   ├── pipeline.py         # inbound (Apply) deck pipeline
│   ├── embeddings.py       # RAG embeddings
│   └── db.py               # Supabase Memory layer
├── db/                     # schema.sql · seed.sql · add_embeddings.sql · add_screening.sql
├── demo_decks/             # synthetic pitch decks (incl. a seeded contradiction)
└── docs/                   # api_contract.md · agent_schemas.md · enrichment_plan.md · runsheet.md
```

---

## Running it

**Memory:** create a Supabase project, then run `db/schema.sql`, `db/add_embeddings.sql`,
`db/add_screening.sql`, and optionally `db/seed.sql` in the SQL editor.

**Agent service:**
```bash
cd agent-service
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env         # add OpenAI / Tavily / Supabase / OpenRegister keys
uvicorn main:app --reload       # http://localhost:8000/docs
```

Capability flags (env) bring the system up in stages: `DB_WIRED`, `SCORING_LIVE`, `MEMO_LIVE`,
`WEB_ENRICH`, `APPLY_LIVE`, `QUERY_LIVE`, `SCREEN_GATES`. Each turns on one part of the pipeline,
so the system is demonstrable end-to-end even before every key is set.

**Frontend:** the Lovable app points at the agent service via `AGENT_SERVICE_URL`.

**End-to-end (outbound):** `POST /thesis` → `POST /scan` → `POST /pipeline` (enrich → screen →
score → memo on selected founders) → `POST /embed?force=true` → `POST /query`.

**End-to-end (inbound):** upload a deck from `demo_decks/` on the Apply page → watch it resolve to
a scored memo, with the seeded contradiction flagged.

---

## Design principles we held to

- Sourcing depth over reasoning polish; a thin honest intelligence layer over deep data.
- The three axes are shown side by side and never collapsed into one number.
- Every conclusion traces to evidence; every gap is stated.
- Cold-start founders are first-class citizens, scored with honest uncertainty.
- The fund thesis is configurable and actively filters the funnel.
