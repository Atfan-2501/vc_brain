"""Canned contract-shaped responses for the H0 integration test.
These mirror the seed data in db/seed.sql so the stubbed API and the seeded DB agree."""

STUB_OPPORTUNITIES = {
    "opportunities": [
        {
            "opportunity_id": "e0000000-0000-0000-0000-000000000001",
            "company_name": "Kessler AI", "founder_name": "Jana Kessler",
            "founder_id": "f0000000-0000-0000-0000-000000000001",
            "stage": "diligence", "source": "inbound", "is_pre_track_record": False,
            "axes": {
                "founder": {"score": 9, "trend": "improving", "verdict": None},
                "market": {"score": 7, "trend": "stable", "verdict": "bullish"},
                "idea_vs_market": {"score": 8, "trend": "improving", "verdict": None},
            },
            "has_contradiction": False,
            "decision": None,
            "first_signal_at": "2026-07-16T09:00:00Z", "decided_at": None,
        },
        {
            "opportunity_id": "e0000000-0000-0000-0000-000000000002",
            "company_name": "VaneLabs", "founder_name": "Marcus Vane",
            "founder_id": "f0000000-0000-0000-0000-000000000002",
            "stage": "screening", "source": "outbound", "is_pre_track_record": False,
            "axes": {
                "founder": {"score": 6, "trend": "stable", "verdict": None},
                "market": {"score": 5, "trend": "stable", "verdict": "neutral"},
                "idea_vs_market": {"score": 4, "trend": "declining", "verdict": None},
            },
            "has_contradiction": True,
            "decision": None,
            "first_signal_at": "2026-07-15T09:00:00Z", "decided_at": None,
        },
        {
            "opportunity_id": "e0000000-0000-0000-0000-000000000003",
            "company_name": "NandaHealth", "founder_name": "Priya Nandakumar",
            "founder_id": "f0000000-0000-0000-0000-000000000003",
            "stage": "screening", "source": "inbound", "is_pre_track_record": True,
            "axes": {
                "founder": {"score": 4, "trend": "stable", "verdict": None},
                "market": {"score": 6, "trend": "improving", "verdict": "neutral"},
                "idea_vs_market": {"score": 5, "trend": "stable", "verdict": None},
            },
            "has_contradiction": True,
            "decision": None,
            "first_signal_at": "2026-07-18T09:00:00Z", "decided_at": None,
        },
    ],
    "generated_at": "2026-07-19T00:00:00Z",
}

STUB_REASONING_LOG = {
    "reasoning_log_id": "log-vane-0001",
    "opportunity_id": "e0000000-0000-0000-0000-000000000002",
    "steps": [
        {"agent": "extraction", "step": 1, "prompt": "deck -> claims",
         "response": {"claims": 2, "missing_data": ["cap table", "financials"]},
         "model": "gpt-4o", "created_at": "2026-07-15T09:01:00Z"},
        {"agent": "verification", "step": 2, "prompt": "$50K MRR with 300 paying teams",
         "response": {"trust_score": 0.2, "verification_status": "contradicted",
                      "contradiction_note": "Launch was 3 weeks ago; MRR implausible."},
         "model": "gpt-4o", "created_at": "2026-07-15T09:02:00Z"},
        {"agent": "axis_scorer", "step": 4, "prompt": "3 independent axes",
         "response": {"founder": 6, "market": 5, "idea_vs_market": 4},
         "model": "gpt-4o", "created_at": "2026-07-15T09:03:00Z"},
        {"agent": "memo", "step": 5, "prompt": "memo + decision",
         "response": {"recommendation": "Request specific info"},
         "model": "gpt-4o", "created_at": "2026-07-15T09:04:00Z"},
    ],
    "generated_at": "2026-07-19T00:00:00Z",
}

STUB_DETAIL = {
    "opportunity_id": "e0000000-0000-0000-0000-000000000002",
    "company_name": "VaneLabs",
    "founder": {
        "founder_id": "f0000000-0000-0000-0000-000000000002", "name": "Marcus Vane",
        "founder_score": 64, "founder_score_interval": 12, "is_pre_track_record": False,
    },
    "axes": {
        "founder": {"score": 6, "trend": "stable", "verdict": None,
                    "rationale": "Solo technical founder, credible OSS launch; limited prior outcomes.",
                    "cited_claim_ids": ["d0000000-0000-0000-0000-000000000006"], "swot": None},
        "market": {"score": 5, "trend": "stable", "verdict": "neutral",
                   "rationale": "CI-cache tooling is crowded; wedge unclear.",
                   "cited_claim_ids": [], "swot": {"strengths": ["OSS traction"],
                   "weaknesses": ["crowded"], "opportunities": ["enterprise CI spend"],
                   "risks": ["incumbents bundle it free"]}},
        "idea_vs_market": {"score": 4, "trend": "declining", "verdict": None,
                           "rationale": "Traction claim contradicts launch timeline; idea needs a sharper wedge.",
                           "cited_claim_ids": ["d0000000-0000-0000-0000-000000000005"], "swot": None},
    },
    "claims": [
        {"claim_id": "d0000000-0000-0000-0000-000000000005",
         "claim_text": "$50K MRR with 300 paying teams", "claim_type": "traction",
         "trust_score": 0.2, "verification_status": "contradicted",
         "verification_evidence_url": "https://news.ycombinator.com/item?id=999001",
         "contradiction_note": "Show HN launch was 3 weeks ago; $50K MRR + 300 paying teams implausible.",
         "source_ref": {"type": "deck", "slide_number": 7}},
        {"claim_id": "d0000000-0000-0000-0000-000000000006",
         "claim_text": "Product launched on Hacker News, 400 upvotes", "claim_type": "traction",
         "trust_score": 0.85, "verification_status": "verified",
         "verification_evidence_url": "https://news.ycombinator.com/item?id=999001",
         "contradiction_note": None, "source_ref": {"type": "web", "url": "news.ycombinator.com/item?id=999001"}},
    ],
    "memo": {
        "company_snapshot": "VaneLabs builds an open-source CI cache for engineering teams.",
        "investment_hypotheses": ["Credible OSS launch signal", "Large CI spend market"],
        "swot": {"strengths": ["OSS traction"], "weaknesses": ["crowded space"],
                 "opportunities": ["enterprise CI"], "risks": ["free incumbents"]},
        "problem_and_product": "CI pipelines are slow; VaneLabs caches build artifacts to cut times.",
        "traction_and_kpis": "HN launch verified (400 upvotes). Revenue claim CONTRADICTED - see log.",
        "optional_sections": {},
        "gaps_flagged": ["Cap table: not disclosed", "Financials: not disclosed", "Verified revenue: missing"],
    },
    "contradictions": [
        {"claim_id": "d0000000-0000-0000-0000-000000000005",
         "note": "Deck claims $50K MRR; landing page / launch was 3 weeks ago.",
         "evidence_url": "https://news.ycombinator.com/item?id=999001"}
    ],
    "decision": {"recommendation": "Request specific info",
                 "rationale": "Strong launch signal but the revenue claim is contradicted.",
                 "most_decisive_missing_datum": "Verified revenue (Stripe export)"},
    "reasoning_log_id": "log-vane-0001",
    "first_signal_at": "2026-07-15T09:00:00Z", "decided_at": None,
    "generated_at": "2026-07-19T00:00:00Z",
}

STUB_QUERY = {
    "parsed_filters": {"sector": "AI infra", "geo": "Berlin", "founder_type": "technical"},
    "results": [{"opportunity_id": "e0000000-0000-0000-0000-000000000001",
                 "company_name": "Kessler AI", "match_reason": "Technical founder, Berlin, AI infra."}],
    "generated_at": "2026-07-19T00:00:00Z",
}

STUB_FOUNDER = {
    "founder_id": "f0000000-0000-0000-0000-000000000001", "name": "Jana Kessler",
    "founder_score": 78, "founder_score_interval": 9, "is_pre_track_record": False,
    "score_history": [
        {"score": 70, "interval": 14, "at": "2026-04-20T00:00:00Z", "trigger_signal_id": None},
        {"score": 75, "interval": 11, "at": "2026-06-19T00:00:00Z", "trigger_signal_id": None},
        {"score": 78, "interval": 9, "at": "2026-07-17T00:00:00Z", "trigger_signal_id": None},
    ],
    "companies": [{"company_id": "c0000000-0000-0000-0000-000000000001", "name": "Kessler AI", "role": "CEO"}],
    "signals": [{"signal_id": "a0000000-0000-0000-0000-000000000002", "source": "github",
                 "source_url": "https://github.com/jkessler/kessler-core", "at": "2026-07-16T00:00:00Z"}],
    "generated_at": "2026-07-19T00:00:00Z",
}
