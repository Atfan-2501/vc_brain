# Lovable prompt — "Run pipeline on selected companies"

Paste into Lovable to add board selection + a run-pipeline action.

---

Add a **multi-select + run-pipeline** capability to the Pipeline Board.

**New endpoint** (already live on the agent service): `POST /pipeline` with body
`{ "opportunity_ids": string[], "steps": ["enrich","score","memo"] }`. Returns `202`
`{ status:"processing", count, steps, generated_at }`. It runs enrich → score → memo on the
selected opportunities in the background. Add `postPipeline(ids, steps)` to `src/lib/agent.ts`
hitting the server proxy like the other calls.

**Selection UI on the Pipeline Board:**
- Each opportunity card gets a small checkbox in its top-left corner. Clicking it toggles
  selection; clicking the card body still opens the detail view (checkbox stops propagation).
- Track selected `opportunity_id`s in component state (a `Set`).
- Add a **sticky action bar** at the top of the board (below the top nav) that appears only when
  ≥1 card is selected. It shows: "`N selected`", a **Clear** link, an optional step multi-select
  (Enrich / Score / Memo — all three checked by default), and a primary button
  **"Run pipeline on selected"**.
- On click: call `postPipeline(selectedIds, selectedSteps)`, then show a toast
  "Running pipeline on N companies…", clear the selection, and start polling.

**Processing + live update:**
- After firing `/pipeline`, mark the selected cards with a subtle "processing" pulse/badge.
- Use TanStack Query `refetchInterval` on `getOpportunities` (e.g. every 4s) while any card is
  processing; stop once those cards have non-null `axes.founder.score`. As scores land, cards
  naturally move Sourcing → Screening → Decision columns and render their three axis scores.
- Keep everything else (three separate axis scores, trend arrows, contradiction dot) unchanged.

**Guardrails:**
- Cap a single run at, say, 10 selected companies (each spends API calls); if more are selected,
  disable the button with a hint "Select up to 10 at a time."
- Don't block the UI — the run is fire-and-forget + poll, never a long synchronous request.

Keep the calm, dense aesthetic. The checkbox and action bar should feel native to the board,
not bolted on.
