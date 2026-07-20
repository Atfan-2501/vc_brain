# Lovable prompt — pipeline progress overlay + screened-out dialog

Paste into Lovable. Two changes: a blurred full-page progress overlay while the pipeline runs,
and a dialog when a founder is screened out by the thesis (so polling stops instead of spinning).

---

Add a **pipeline progress overlay** and a **screened-out dialog**.

## 1. Progress overlay (while the pipeline runs)

When a pipeline run is triggered (either "Run pipeline on selected" from the board, or
"Run pipeline" on an opportunity detail page):

- **Blur and lock the whole page**: overlay the app with a backdrop
  (`backdrop-filter: blur(6px)`, semi-opaque neutral scrim) so the UI behind is visibly inert.
  Block interaction while it runs.
- Center a calm card titled **"Running the pipeline"** with the company name(s), or
  "N companies" for a multi-select run.
- Show the **four stages as a vertical checklist**, each with pending / running / done state
  (spinner → check). Derive each from the polled `GET /opportunities/:id` response:

  | Stage | Label | Done when |
  |---|---|---|
  | 1 | **Enriching** — register, GitHub, web | `claims.length > 0` OR `founder.founder_score != null` |
  | 2 | **Screening & scoring** — 3 axes | `axes.founder.score != null` |
  | 3 | **Writing memo** — decision | `decision.recommendation != null` |
  | 4 | **Indexing** — Ask the Brain | `embedded === true` |

  The stage after the last completed one shows as "running" with a spinner. Add a subtle caption:
  "This can take a minute or two per company."

- For a **multi-select run**, also show aggregate progress: "2 of 5 complete" with a thin
  progress bar; poll `GET /opportunities` and count how many selected ids have
  `axes.founder.score != null` (or a decision).
- **Dismiss the overlay** when all four stages are done (or, for multi-select, when all selected
  are complete). Then refresh the underlying view so the new scores/memo render.
- Include a small **"Run in background"** text button that closes the overlay and keeps polling
  quietly, so the user isn't trapped.
- **Timeout guard:** if nothing changes for 3 minutes, close the overlay and show a toast
  "Still processing — refresh shortly."

## 2. Screened-out dialog (thesis gate)

While polling, if the response has **`passed_screen === false`** (or `thesis_fit === "off_thesis"`):

- **Stop polling immediately** — do NOT keep waiting for scores. This founder will never get
  axis scores or a memo by design.
- Close the progress overlay and open a **dialog**:
  - Title: **"Screened out — off thesis"**
  - Body: the company name, then `screen_rationale` verbatim as the explanation, and a line:
    "This founder doesn't match your current investment thesis, so full analysis was skipped to
    save time and cost."
  - Show the `thesis_fit` value as a small chip (`off_thesis` / `partial`).
  - Buttons: **"Edit thesis"** (routes to `/thesis`), **"View company"** (routes to the detail
    page), and **"Close"**.
- On the board, mark that card with a muted "off-thesis" chip so it's visually distinct from
  cards that are still processing.

Keep the calm, dense aesthetic — the overlay should feel like a considered status panel, not a
loading spinner. Neutral surfaces, one accent for the running stage, hairline borders.
