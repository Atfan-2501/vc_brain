# Lovable prompt — "Run pipeline" on the opportunity detail page

Paste into Lovable. Lets a user run the reasoning pipeline on a single company from its detail
page (e.g. after clicking through from an Ask the Brain result).

---

On the **Opportunity detail page** (`/opportunities/$opportunity_id`), add a **Run pipeline** action.

**Endpoint (already live):** `POST /pipeline` with body
`{ "opportunity_ids": ["<this id>"], "steps": ["enrich","score","memo"] }` → `202`
`{ status:"processing", count, steps, generated_at }`. It runs enrich → score → memo on that one
opportunity in the background (it resolves the founder itself). Reuse the existing
`postPipeline(ids, steps)` client (add it if not present).

**UI:**
- In the detail header, add a primary button **"Run pipeline"** (or **"Re-run pipeline"** if the
  opportunity already has axis scores). Next to it, a small popover with three checkboxes —
  Enrich / Score / Memo — all checked by default, so the user can run a subset.
- On click: call `postPipeline([opportunity_id], selectedSteps)`, toast "Running pipeline…",
  and enter a **processing state** on the page.

**Processing + live refresh:**
- While processing, show a calm inline banner ("Running enrich → score → memo · updating…") and a
  skeleton/pulse over the axis scores + memo sections.
- Use TanStack Query `refetchInterval` (~4s) on `getOpportunity(id)` while processing; stop once
  `axes.founder.score` is non-null AND `decision.recommendation` is non-null, then clear the
  processing state so the freshly-scored memo + SWOT + decision render.
- If the poll runs >90s, stop and show "Still processing — reload shortly" with a manual refresh.

**Guardrails:**
- Disable the button while a run is in flight for this opportunity.
- Steps depend on server flags; if a step is off server-side it's simply skipped — the UI doesn't
  need to know, just reflect whatever the refetched data shows.

Keep the calm, dense aesthetic; the button belongs in the header next to the stage/source badges.
This makes the Ask-the-Brain → open company → score-it flow one click.
