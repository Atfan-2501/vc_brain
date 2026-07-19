"""OpenAI structured-output JSON schemas — the shapes sent TO OpenAI.
Mirror docs/agent_schemas.md. Distinct from contracts.py (shapes sent to the frontend).
Use with client.chat.completions.create(response_format={"type":"json_schema", ...})."""

EXTRACTION_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "claims": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "properties": {
                "claim_text": {"type": "string"},
                "claim_type": {"type": "string",
                    "enum": ["traction", "team", "market", "tech", "financial", "other"]},
                "source_ref": {"type": "object", "additionalProperties": False,
                    "properties": {"type": {"type": "string", "enum": ["deck", "web"]},
                                   "slide_number": {"type": ["integer", "null"]},
                                   "url": {"type": ["string", "null"]}},
                    "required": ["type", "slide_number", "url"]},
                "confidence": {"type": "number"},
            },
            "required": ["claim_text", "claim_type", "source_ref", "confidence"]}},
        "missing_data": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["claims", "missing_data"],
}

VERIFICATION_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "claim_id": {"type": "string"},
        "trust_score": {"type": "number"},
        "verification_status": {"type": "string",
            "enum": ["verified", "unverified", "contradicted"]},
        "verification_evidence_url": {"type": ["string", "null"]},
        "contradiction_note": {"type": ["string", "null"]},
        "rationale": {"type": "string"},
    },
    "required": ["claim_id", "trust_score", "verification_status",
                 "verification_evidence_url", "contradiction_note", "rationale"],
}

SCREENER_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "passes_screen": {"type": "boolean"},
        "thesis_fit": {"type": "string", "enum": ["strong", "partial", "off_thesis"]},
        "kill_reasons": {"type": "array", "items": {"type": "string"}},
        "rationale": {"type": "string"},
        "cited_claim_ids": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["passes_screen", "thesis_fit", "kill_reasons", "rationale", "cited_claim_ids"],
}

AXIS_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "axis": {"type": "string", "enum": ["founder", "market", "idea_vs_market"]},
        "score": {"type": "integer"},
        "trend": {"type": "string", "enum": ["improving", "declining", "stable"]},
        "verdict": {"type": ["string", "null"], "enum": ["bullish", "neutral", "bear", None]},
        "swot": {"type": ["object", "null"], "additionalProperties": False,
            "properties": {"strengths": {"type": "array", "items": {"type": "string"}},
                           "weaknesses": {"type": "array", "items": {"type": "string"}},
                           "opportunities": {"type": "array", "items": {"type": "string"}},
                           "risks": {"type": "array", "items": {"type": "string"}}},
            "required": ["strengths", "weaknesses", "opportunities", "risks"]},
        "rationale": {"type": "string"},
        "cited_claim_ids": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["axis", "score", "trend", "verdict", "swot", "rationale", "cited_claim_ids"],
}

FOUNDER_SCORE_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "founder_score": {"type": "number"},
        "founder_score_interval": {"type": "number"},
        "is_pre_track_record": {"type": "boolean"},
        "drivers": {"type": "array", "items": {"type": "string"}},
        "cited_signal_ids": {"type": "array", "items": {"type": "string"}},
        "rationale": {"type": "string"},
    },
    "required": ["founder_score", "founder_score_interval", "is_pre_track_record",
                 "drivers", "cited_signal_ids", "rationale"],
}

MEMO_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "company_snapshot": {"type": "string"},
        "investment_hypotheses": {"type": "array", "items": {"type": "string"}},
        "swot": {"type": "object", "additionalProperties": False,
            "properties": {"strengths": {"type": "array", "items": {"type": "string"}},
                           "weaknesses": {"type": "array", "items": {"type": "string"}},
                           "opportunities": {"type": "array", "items": {"type": "string"}},
                           "risks": {"type": "array", "items": {"type": "string"}}},
            "required": ["strengths", "weaknesses", "opportunities", "risks"]},
        "problem_and_product": {"type": "string"},
        "traction_and_kpis": {"type": "string"},
        "optional_sections": {"type": "object"},
        "gaps_flagged": {"type": "array", "items": {"type": "string"}},
        "cited_claim_ids": {"type": "array", "items": {"type": "string"}},
        "recommendation": {"type": "string",
            "enum": ["Invest $100K", "Decline", "Request specific info"]},
        "decision_rationale": {"type": "string"},
        "most_decisive_missing_datum": {"type": "string"},
    },
    "required": ["company_snapshot", "investment_hypotheses", "swot", "problem_and_product",
                 "traction_and_kpis", "gaps_flagged", "cited_claim_ids",
                 "recommendation", "decision_rationale", "most_decisive_missing_datum"],
}

QUERY_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "parsed_filters": {"type": "object"},
        "semantic_terms": {"type": "array", "items": {"type": "string"}},
        "rationale": {"type": "string"},
    },
    "required": ["parsed_filters", "semantic_terms", "rationale"],
}

SYSTEM_BOILERPLATE = (
    "You are a VC analyst agent. Only assert what the evidence supports. If evidence is "
    "absent, list it in missing_data - never infer or fabricate numbers. Cite the claim "
    "IDs your reasoning rests on. Score through the active thesis provided."
)
