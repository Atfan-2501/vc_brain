# Agent Output Schemas (OpenAI structured outputs)

One schema per agent. Pass each as a `response_format` json_schema (or function tool).
Universal rule baked into every schema: `rationale`, `cited_claim_ids`, `confidence`,
and `missing_data` where applicable — this is how Agentic Traceability + honesty fall out
for free. Every agent call is logged to `reasoning_log`.

System-prompt boilerplate to reuse everywhere:
> "You are a VC analyst agent. Only assert what the evidence supports. If evidence is
> absent, list it in `missing_data` — never infer or fabricate numbers. Cite the claim
> IDs your reasoning rests on. Score through the active thesis provided."

---

## 1. Extraction Agent — deck/page → claims
Input: deck PDF (multimodal) or scraped page text + company_id.
```json
{
  "type": "object",
  "properties": {
    "claims": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "claim_text":  { "type": "string" },
          "claim_type":  { "type": "string", "enum": ["traction","team","market","tech","financial","other"] },
          "source_ref":  { "type": "object",
                           "properties": { "type": {"type":"string","enum":["deck","web"]},
                                           "slide_number": {"type":["integer","null"]},
                                           "url": {"type":["string","null"]} },
                           "required": ["type"] },
          "confidence":  { "type": "number", "minimum": 0, "maximum": 1 }
        },
        "required": ["claim_text","claim_type","source_ref","confidence"]
      }
    },
    "missing_data": { "type": "array", "items": {"type":"string"} }
  },
  "required": ["claims","missing_data"]
}
```

## 2. Verification Agent — per claim → Trust Score
Input: one claim + Tavily search results. Run per claim (or batched).
```json
{
  "type": "object",
  "properties": {
    "claim_id":            { "type": "string" },
    "trust_score":         { "type": "number", "minimum": 0, "maximum": 1 },
    "verification_status": { "type": "string", "enum": ["verified","unverified","contradicted"] },
    "verification_evidence_url": { "type": ["string","null"] },
    "contradiction_note":  { "type": ["string","null"] },
    "rationale":           { "type": "string" }
  },
  "required": ["claim_id","trust_score","verification_status","rationale"]
}
```
Rubric in prompt: 0.9+ externally verified by independent source · 0.6–0.9 consistent but
not directly confirmed · 0.3–0.6 plausible/unverifiable · <0.3 contradicted or implausible.
Internal claims (revenue, cap table) stay `unverified` at honest low-mid trust — never inflated.

## 3. Screener Agent — fast viability filter vs thesis
Input: claims summary + active thesis.
```json
{
  "type": "object",
  "properties": {
    "passes_screen":   { "type": "boolean" },
    "thesis_fit":      { "type": "string", "enum": ["strong","partial","off_thesis"] },
    "kill_reasons":    { "type": "array", "items": {"type":"string"} },
    "rationale":       { "type": "string" },
    "cited_claim_ids": { "type": "array", "items": {"type":"string"} }
  },
  "required": ["passes_screen","thesis_fit","rationale","cited_claim_ids"]
}
```

## 4. Axis Scorer — THREE SEPARATE CALLS (never combine)
Call once per axis with `axis` = founder | market | idea_vs_market. Market adds verdict+SWOT.
```json
{
  "type": "object",
  "properties": {
    "axis":            { "type": "string", "enum": ["founder","market","idea_vs_market"] },
    "score":           { "type": "integer", "minimum": 1, "maximum": 10 },
    "trend":           { "type": "string", "enum": ["improving","declining","stable"] },
    "verdict":         { "type": ["string","null"], "enum": ["bullish","neutral","bear",null] },
    "swot":            { "type": ["object","null"],
                         "properties": { "strengths":{"type":"array","items":{"type":"string"}},
                                         "weaknesses":{"type":"array","items":{"type":"string"}},
                                         "opportunities":{"type":"array","items":{"type":"string"}},
                                         "risks":{"type":"array","items":{"type":"string"}} } },
    "rationale":       { "type": "string" },
    "cited_claim_ids": { "type": "array", "items": {"type":"string"} }
  },
  "required": ["axis","score","trend","rationale","cited_claim_ids"]
}
```
`verdict` + `swot` are non-null ONLY for the market axis. Founder axis consumes the
Founder Score as one input. Do NOT average the three results anywhere.

## 5. Founder Score Updater — persistent, per person
Input: founder's full signal history.
```json
{
  "type": "object",
  "properties": {
    "founder_score":          { "type": "number", "minimum": 0, "maximum": 100 },
    "founder_score_interval": { "type": "number", "minimum": 0 },
    "is_pre_track_record":    { "type": "boolean" },
    "drivers":       { "type": "array", "items": {"type":"string"} },
    "cited_signal_ids": { "type": "array", "items": {"type":"string"} },
    "rationale":     { "type": "string" }
  },
  "required": ["founder_score","founder_score_interval","is_pre_track_record","rationale"]
}
```
Cold-start: high interval, `is_pre_track_record: true`, drivers rely on deck specificity +
public-footprint analysis. Append every result to `founder_score_history`.

## 6. Memo Agent — required 5 sections + gaps
Input: claims + 3 axis outputs + founder score.
```json
{
  "type": "object",
  "properties": {
    "company_snapshot":      { "type": "string" },
    "investment_hypotheses": { "type": "array", "items": {"type":"string"} },
    "swot": { "type": "object",
              "properties": { "strengths":{"type":"array","items":{"type":"string"}},
                              "weaknesses":{"type":"array","items":{"type":"string"}},
                              "opportunities":{"type":"array","items":{"type":"string"}},
                              "risks":{"type":"array","items":{"type":"string"}} },
              "required": ["strengths","weaknesses","opportunities","risks"] },
    "problem_and_product":   { "type": "string" },
    "traction_and_kpis":     { "type": "string" },
    "optional_sections":     { "type": "object" },
    "gaps_flagged":          { "type": "array", "items": {"type":"string"} },
    "cited_claim_ids":       { "type": "array", "items": {"type":"string"} }
  },
  "required": ["company_snapshot","investment_hypotheses","swot","problem_and_product","traction_and_kpis","gaps_flagged","cited_claim_ids"]
}
```
Prompt rule: every sentence references claim IDs; unverifiable numbers show their trust
score; unavailable ones go in `gaps_flagged` ("Cap table: not disclosed"). Padding penalized.

## 7. Decision — final recommendation
Usually folded into the memo call or a thin follow-up.
```json
{
  "type": "object",
  "properties": {
    "recommendation": { "type": "string", "enum": ["Invest $100K","Decline","Request specific info"] },
    "rationale":      { "type": "string" },
    "most_decisive_missing_datum": { "type": "string" },
    "cited_claim_ids": { "type": "array", "items": {"type":"string"} }
  },
  "required": ["recommendation","rationale","most_decisive_missing_datum"]
}
```

## 8. Query Agent — NL compound query, one pass
```json
{
  "type": "object",
  "properties": {
    "parsed_filters": { "type": "object" },
    "semantic_terms": { "type": "array", "items": {"type":"string"} },
    "rationale":      { "type": "string" }
  },
  "required": ["parsed_filters"]
}
```
Then execute parsed_filters as SQL WHERE + optional embedding search in ONE pass over Memory.
