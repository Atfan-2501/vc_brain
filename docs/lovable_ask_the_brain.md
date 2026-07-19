# Lovable prompt — Ask the Brain (RAG answer + ranked results)

Paste into Lovable to upgrade the Ask the Brain view for the new RAG response.

---

Update the **Ask the Brain** page (`/ask`) for the new response shape from `POST /query`.

The response is now:
```json
{
  "answer": "NeuroForge is the strongest match: a Munich AI-infra founder with a heavy GitHub footprint.",
  "results": [
    { "opportunity_id": "uuid", "company_name": "NeuroForge",
      "founder_name": "Amir Haddad", "match_reason": "AI infra chips + 800-star GitHub, Munich",
      "relevance": 0.83 }
  ],
  "parsed_filters": {},
  "generated_at": "..."
}
```

Changes:
- **Answer panel:** above the results, render `answer` prominently in a calm callout card
  (slightly larger text, a subtle left accent border in the neutral ink color). This is the
  synthesized natural-language answer — it's the headline of the response. If `answer` is empty,
  hide the panel.
- **Result rows:** for each item in `results` show `company_name` (links to
  `/opportunities/$opportunity_id`), `founder_name` in muted text, the `match_reason` as the
  supporting line, and a small mono **relevance badge** on the right (e.g. `0.83`) colored on a
  ramp: ≥0.8 strong, 0.6–0.8 medium, <0.6 faint. If `relevance` is null, omit the badge.
- Remove/ignore the old `parsed_filters` chips row — it's empty now (RAG doesn't use rigid
  filters). Keep the search box and its submit/loading states unchanged.
- Empty state: if `results` is empty, show the `answer` text (it explains why, e.g. "no companies
  indexed yet") instead of a blank list.

Keep the dense, calm aesthetic. The answer panel should read like a briefing line, the results
like a ranked shortlist.
