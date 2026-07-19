# 14-Hour Solo Runsheet — VC Brain (two-stack, no cuts under pressure)

Two stacks, you own the integration: **Lovable (React + Supabase)** as the app +
Memory layer, **agent service (FastAPI or Node)** as the brain. They meet only at the
frozen REST contract (`01_api_contract.md`). Judging weights drive every trade-off:
Data/Sourcing 30% · Investment Utility 30% · Analysis/Trust 25% · UX 15%.

Prep artifacts already in hand: API contract, schema SQL, seed SQL, agent schemas,
Lovable prompt. Load them at hour 0 and you skip the slowest setup.

---

## H0 – H1 · Setup (both stacks in parallel-ish)
- [ ] Secrets ready: OPENAI_API_KEY, TAVILY_API_KEY, Supabase URL + service key. Smoke-test one OpenAI structured call + one Tavily search.
- [ ] Supabase: run `02_schema.sql`, then `03_seed_data.sql`. Confirm 8 founders, seeded contradictions present.
- [ ] Agent service: scaffold FastAPI/Node, stub all 7 endpoints returning hardcoded JSON matching the contract. Deploy somewhere reachable (Railway/Render/Fly) → get `AGENT_SERVICE_URL`.
- [ ] Lovable: paste `05_lovable_prompt.md`. Set `AGENT_SERVICE_URL` secret. Verify pipeline board renders the seeded opportunities against the STUBBED endpoints.
- **GATE H1:** app talks to service; both read the same Supabase; contract holds end-to-end with fake data. Integration is proven before any real logic exists — this is the point of stubbing first.

## H1 – H6 · Vertical slice, real logic (the make-or-break block)
Wire the agents behind the endpoints, in pipeline order. Use `04_agent_schemas.md`.
- [ ] `POST /apply`: deck PDF → **Extraction Agent** (multimodal) → insert claims.
- [ ] **Verification Agent**: per claim, Tavily search → trust_score + status. Must catch the seeded VaneLabs "$50K MRR vs launched 3 weeks ago" contradiction.
- [ ] **Screener** → thesis-fit filter (pull active thesis from DB).
- [ ] **Axis Scorer**: THREE separate calls → store scores + trends + rationale + cited_claim_ids. Never average.
- [ ] **Memo Agent**: 5 required sections, claims cited, `gaps_flagged` for missing cap table/financials.
- [ ] Decision + set `first_signal_at` / `decided_at`.
- [ ] Log every agent call to `reasoning_log`.
- **GATE H6:** one real deck goes in → memo + decision come out, fully automated, with one contradiction visibly caught and cap table flagged. If not here by H6, keep pushing this slice — do NOT jump ahead. Everything else is worthless without it.

## H6 – H9 · Sourcing depth (the 30% differentiator — protect this block)
- [ ] **Outbound Scanner** (`POST /scan`): two Tavily jobs — Show HN + ProductHunt — → insert `signals`.
- [ ] Detected founders → same funnel → appear as `source: outbound` opportunities. Both funnels converge, proven on screen.
- [ ] Dedup: hash on (source, source_url) + name match. Merge into one founder record.
- [ ] **Founder Score**: 0–100 ± interval, recompute on new signals, append to history. Cold-start path: wide interval, `is_pre_track_record`, footprint-based reasoning, "pre-track-record" label.
- **GATE H9:** run a scan live → an unknown founder appears and gets scored like an inbound applicant; a cold-start founder shows a wide interval.

## H9 – H11 · Trust & traceability surface (Analysis 25%)
- [ ] Evidence chips wired: click a memo claim → source ref + trust score + status (Lovable follow-up prompt #2).
- [ ] Reasoning-log viewer (follow-up prompt #3) — even a plain table proves Agentic Traceability.
- [ ] `POST /query`: NL compound query → parsed filters → one-pass SQL over Memory. Show the parsed filters in the UI.
- **GATE H11:** click any conclusion → trace to its evidence. This is the highest-leverage stretch goal; it's in.

## H11 – H13 · UX pass (15% — legibility over polish)
- [ ] Pipeline board: three side-by-side axis scores + trend arrows, contradiction dots, pre-track-record labels (follow-up prompt #1).
- [ ] Founder profile score chart with uncertainty band (prompt #4).
- [ ] Thesis form wired through scoring end-to-end (change thesis → rescore differs).
- [ ] Speed meter reads the `speed_metric` view.
- [ ] Loading/empty/error states everywhere (prompt #5).

## H13 – H14 · Demo lock
- [ ] Pre-run the full pipeline on seed data. **No live external API calls on stage** — cache/canned results.
- [ ] Keep Ricci Tools or Okonkwo AI without an opportunity row → run it live deck-in→memo-out as beat 3.
- [ ] Two slides: (1) cold-start method, (2) public-footprint research question (Area of Research 3 — judges explicitly reward this).
- [ ] Rehearse the 6-beat script below once, timed.

### 6-beat demo script
1. Set the thesis → fund lens is live.
2. Run outbound scan → an unknown founder surfaces and is auto-scored.
3. Cold applicant with a contradiction applies → Verification Agent catches it on screen.
4. Open the memo → evidence chips, trust badges, "Cap table: not disclosed" gap.
5. Decision rendered in minutes → speed meter shown.
6. Same founder returns later → Founder Score remembered, trend visible.

---

## Never cut (even solo, even behind)
Outbound sourcing · three independent axes · per-claim trust with one caught
contradiction · gap-flagging memo · cold-start handling.

## If genuinely drowning (last-resort order)
1. Drop the second outbound channel (keep one, still "outbound works").
2. Reasoning-log viewer → a JSON dump instead of a styled panel.
3. NL query → 3 hardcoded example queries instead of live parse.
Never touch the never-cut list. A thin honest slice beats a broad broken one.

## Solo survival rules
- Stub endpoints FIRST, real logic SECOND — never debug integration and AI logic at once.
- Commit after every green gate. Deploy early, deploy often.
- When a Tavily/OpenAI call flakes, cache the good response immediately as demo fallback.
- Timebox every agent to "works, ugly." Polish only in H11–13.
