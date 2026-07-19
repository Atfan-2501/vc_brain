# Enrichment Plan — turning thin Munich records into scorable founders

Enrichment does not replace the pipeline; it FEEDS it. Each source produces **signals → claims**
(every one with provenance + a Trust Score), which flow into the Founder Score and the 3-axis
scorer. "Enrich" = generate evidence for records that arrive thin.

## Sources, cheapest-first (exhaust free before spending)

| Tier | Source | Cost | Produces | Feeds |
|------|--------|------|----------|-------|
| 0 | OpenRegister detail (already fetched) | free | revenue, net income, employees, business purpose, website, social handles | Founder + Market axes; gap flags |
| 1 | GitHub API | free (token → 5000/h) | repos, stars, languages, commit freshness, followers | Founder axis (cold-start core) |
| 2 | Tavily web search | cheap | personal site, press, LinkedIn URL, product/traction, market + competitors | all three axes |
| 3 | OpenAI (existing agents) | per-call | claims from text, Trust Scores, contradiction catch, Founder Score, axis scores | Decision + memo |

LinkedIn is **never scraped** (ToS). We find the public profile URL via Tavily and treat it as a
pointer, not scraped content.

## The cold-start research angle (the 30% lever)

The brief rewards operationalizing "how much do public footprints predict founder success."
Per founder we compute footprint features — GitHub activity, prior-startup signals, domain-expertise
density, recognition — and emit a **Founder Score with a wide uncertainty interval** labelled
"pre-track-record." Rich footprint → interval narrows; thin footprint → stays wide but still scorable.
That is exactly the behaviour the challenge calls out.

## Honesty controls (baked in)

- Every claim carries its source URL + Trust Score. Official-register financials score high (0.9);
  a name-only GitHub match is **capped by `match_confidence`** so it never reads as certain.
- Missing data is flagged, never invented ("Cap table: not disclosed").
- Identity resolution is explicit: known handle from the register → 0.9; name+Munich search → 0.5–0.75.

## Efficiency

- Runs **offline / batch** (like the harvest), never live on stage.
- **Bounded** per founder: 1 GitHub resolve + (later) 2–3 Tavily searches.
- **Cached as signals** — nothing is re-fetched; re-runs skip already-enriched founders.

## Module shape (`agent-service/enrichment/`)

- `openregister_extract.py` — Tier 0: register dict → claims + founder handles + gap flags. **[built]**
- `github.py` — Tier 1: resolve founder → footprint features → signal + claims. **[built]**
- `web.py` — Tier 2: Tavily footprint / traction / market. *[next]*
- `enrich.py` — orchestrator: per founder run the tiers, persist, hand off to scoring. **[Tier 0+1 built]**

## Build order

1. ✅ Capture rich OpenRegister fields in the harvest (financials/socials preserved).
2. ✅ Tier 0 extractor — instant claims from data already paid for.
3. ✅ GitHub connector — highest-signal free source.
4. ⬜ Wire `enrich_all()` DB batch loop + a `/enrich` trigger; feed Founder Score with cold-start interval.
5. ⬜ Tier 2 Tavily + reuse extraction/verification for full claims + Trust Scores.
6. ⬜ Axis scorer consumes everything → real SWOT + three scores.

## Trigger model

Batch by default (`enrich_all()`, deliberate, cost-controlled) plus a per-founder `/enrich/:id`
for the live demo moment ("watch us enrich this founder now"). Not automatic on `/scan`.
