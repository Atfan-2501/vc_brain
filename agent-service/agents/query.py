"""Query Agent — natural-language COMPOUND query -> structured filters, executed in ONE pass
over Memory. Multi-attribute reasoning: 'technical founder, Munich, AI infra, pre-track-record'
resolves as a single query, not five manual filters."""
from schemas import QUERY_SCHEMA
from ._common import call_structured

_FILTER_GUIDE = (
    "Map the query to these filter fields (leave a field null if the query doesn't mention it): "
    "sector (e.g. 'AI infra', 'devtools', 'fintech'), geography (e.g. 'Munich'), "
    "stage (sourcing|screening|diligence|decision), source (inbound|outbound), "
    "min_founder_score (0-100), is_pre_track_record (true for early/unproven founders), "
    "keyword (any other free-text term to match on company name or sector). "
    "Put softer intent words in semantic_terms."
)


def run_query(q: str) -> dict:
    parsed = call_structured("query", QUERY_SCHEMA,
                             f"Parse this compound query into filters:\n{q}",
                             extra_system=_FILTER_GUIDE)
    filters = parsed["parsed_filters"]
    results = _execute(filters)
    return {"parsed_filters": filters, "results": results}


def _execute(filters: dict) -> list[dict]:
    """One pass over Memory: opportunities joined to companies + founders, filtered."""
    import db
    return db.query_opportunities(filters)
