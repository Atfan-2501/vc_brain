# REST API Contract — VC Brain (FROZEN)

The single integration point between the Lovable app (client) and the agent service
(FastAPI/Node, holds OpenAI + Tavily keys). Freeze this before writing either side.
Base URL: `${AGENT_SERVICE_URL}`. All bodies JSON unless noted. All responses include
`generated_at` (ISO-8601). Errors: `{ "error": string, "detail"?: string }` + HTTP status.

---

## POST /thesis
Save/replace the active fund lens. Everything downstream is scored through this.

Request:
```json
{
  "sectors": ["AI infra", "devtools"],
  "stages": ["pre-seed", "seed"],
  "geographies": ["EU", "US"],
  "check_size_usd": 100000,
  "ownership_target_pct": 8,
  "risk_appetite": "high"
}
```
Response `200`:
```json
{ "thesis_id": "uuid", "active": true, "generated_at": "..." }
```

---

## POST /apply
Minimum inbound bar: deck + company name. Creates an opportunity and kicks off the
full pipeline (extract → verify → screen → 3-axis → memo → decision) async.
`multipart/form-data`: `company_name` (string, required), `deck_file` (PDF, required),
optional `founder_name`, `founder_links[]`.

Response `202` (returns IMMEDIATELY; the pipeline runs in the background — do not block on it):
```json
{ "opportunity_id": "uuid", "status": "processing", "first_signal_at": "...", "generated_at": "..." }
```
Client then polls `GET /opportunities/:id` until `decision.recommendation` is non-null.

---

## GET /opportunities
Pipeline board data. Query params: `stage?`, `thesis_id?`.

Response `200`:
```json
{
  "opportunities": [
    {
      "opportunity_id": "uuid",
      "company_name": "Acme",
      "founder_name": "Jane Doe",
      "founder_id": "uuid",
      "stage": "screening",
      "source": "inbound",
      "is_pre_track_record": false,
      "axes": {
        "founder":       { "score": 8, "trend": "improving", "verdict": null },
        "market":        { "score": 4, "trend": "stable",    "verdict": "bear" },
        "idea_vs_market":{ "score": 6, "trend": "improving", "verdict": null }
      },
      "has_contradiction": false,
      "decision": null,
      "first_signal_at": "...",
      "decided_at": null
    }
  ],
  "generated_at": "..."
}
```
NOTE: `axes` is always three separate objects. Never a blended number.
`has_contradiction` is a board-level convenience flag (true if any claim on the opportunity
is `contradicted`) so the pipeline card can show the red dot without fetching full detail.

---

## GET /opportunities/:id
Full detail: claims, per-axis rationale, memo, contradictions, reasoning log ref.

Response `200`:
```json
{
  "opportunity_id": "uuid",
  "company_name": "Acme",
  "founder": { "founder_id": "uuid", "name": "Jane Doe",
               "founder_score": 62, "founder_score_interval": 18,
               "is_pre_track_record": false },
  "axes": {
    "founder":        { "score": 8, "trend": "improving", "rationale": "...", "cited_claim_ids": ["uuid"] },
    "market":         { "score": 4, "trend": "stable", "verdict": "bear",
                        "swot": { "strengths": [], "weaknesses": [], "opportunities": [], "risks": [] },
                        "rationale": "...", "cited_claim_ids": ["uuid"] },
    "idea_vs_market": { "score": 6, "trend": "improving", "rationale": "...", "cited_claim_ids": ["uuid"] }
  },
  "claims": [
    { "claim_id": "uuid", "claim_text": "ARR $40K", "claim_type": "traction",
      "trust_score": 0.35, "verification_status": "unverified",
      "verification_evidence_url": null, "contradiction_note": null,
      "source_ref": { "type": "deck", "slide_number": 7 } }
  ],
  "memo": {
    "company_snapshot": "...",
    "investment_hypotheses": ["..."],
    "swot": { "strengths": [], "weaknesses": [], "opportunities": [], "risks": [] },
    "problem_and_product": "...",
    "traction_and_kpis": "...",
    "optional_sections": { "team_history": "...", "competition": "..." },
    "gaps_flagged": ["Cap table: not disclosed", "Financials: not disclosed"]
  },
  "contradictions": [
    { "claim_id": "uuid", "note": "Deck claims $50K MRR; landing page launched 3 weeks ago",
      "evidence_url": "https://..." }
  ],
  "decision": { "recommendation": "Request specific info",
                "rationale": "...",
                "most_decisive_missing_datum": "Verified revenue / Stripe export" },
  "reasoning_log_id": "uuid",
  "first_signal_at": "...", "decided_at": "...",
  "generated_at": "..."
}
```

---

## POST /query
Multi-attribute natural-language compound query, resolved in ONE pass.

Request: `{ "q": "technical founder, Berlin, AI infra, enterprise traction, no prior VC backing" }`

Response `200`:
```json
{
  "parsed_filters": { "sector": "AI infra", "geo": "Berlin", "founder_type": "technical",
                      "traction": "enterprise", "prior_vc": false },
  "results": [ { "opportunity_id": "uuid", "company_name": "Acme", "match_reason": "..." } ],
  "generated_at": "..."
}
```

---

## POST /scan
Trigger an outbound sourcing scan (also runnable on cron). Body optional:
`{ "channels": ["show_hn", "producthunt"] }`.

Response `202`:
```json
{ "scan_id": "uuid", "channels": ["show_hn","producthunt"], "status": "scanning", "generated_at": "..." }
```
Detected founders become `signals` → scored through the SAME funnel → appear as
`source: "outbound"` opportunities in GET /opportunities.

---

## GET /reasoning-log/:id
Agentic Traceability — the step-level chain-of-thought behind an opportunity's memo.
The memo footer's "Reasoning log →" link resolves here via `reasoning_log_id`.

Response `200`:
```json
{
  "reasoning_log_id": "uuid",
  "opportunity_id": "uuid",
  "steps": [
    { "agent": "verification", "step": 2, "prompt": "...", "response": {...},
      "model": "gpt-4o", "created_at": "..." }
  ],
  "generated_at": "..."
}
```

---

## GET /founders/:id
Profile + persistent Founder Score history + cross-company timeline.

Response `200`:
```json
{
  "founder_id": "uuid", "name": "Jane Doe",
  "founder_score": 62, "founder_score_interval": 18,
  "is_pre_track_record": false,
  "score_history": [ { "score": 55, "interval": 25, "at": "...", "trigger_signal_id": "uuid" } ],
  "companies": [ { "company_id": "uuid", "name": "Acme", "role": "CEO" } ],
  "signals": [ { "signal_id": "uuid", "source": "github", "source_url": "...", "at": "..." } ],
  "generated_at": "..."
}
```

---

## Contract rules (do not drift)
- Three axes are always three fields. No endpoint ever returns an averaged score.
- Every claim carries `trust_score` + `verification_status` + a source ref. No claim without provenance.
- Missing data is a string in `gaps_flagged`, never a fabricated value.
- `first_signal_at` and `decided_at` are set on every opportunity → speed metric = median(decided_at − first_signal_at).
- Founder Score is on the founder object, separate from the Founder axis score.
