"""Query Agent — NL compound query -> structured filters, executed in ONE pass. H9-H11.
Multi-attribute reasoning: 'technical founder, Berlin, AI infra, enterprise traction,
no prior VC backing' resolves as a single query, not five manual filters."""
from schemas import QUERY_SCHEMA
from ._common import call_structured


def run_query(q: str) -> dict:
    parsed = call_structured("query", QUERY_SCHEMA, f"Parse into filters + semantic terms: {q}")
    results = _execute(parsed["parsed_filters"], parsed.get("semantic_terms", []))
    return {"parsed_filters": parsed["parsed_filters"], "results": results}


def _execute(filters: dict, semantic_terms: list[str]) -> list[dict]:
    """Translate filters to a single Supabase query over opportunities/founders/companies.
    TODO: build WHERE from filters; optionally embedding-rank by semantic_terms. One pass."""
    raise NotImplementedError("wire in H9-H11")
