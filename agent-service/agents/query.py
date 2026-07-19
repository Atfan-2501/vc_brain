"""Ask the Brain — RAG over Memory. Retrieve by semantic similarity over comprehensive per-company
documents, then let an LLM re-rank the retrieved candidates and synthesize an answer. This beats
rigid attribute filtering: 'a technical founder pivoting into climate' matches on substance, and a
missed field never zeroes out results."""
from schemas import RERANK_SCHEMA
from ._common import call_structured

TOP_K = 15          # how many candidates to retrieve before LLM re-ranking


def run_query(q: str) -> dict:
    import db
    candidates = db.semantic_search(q, top_k=TOP_K)
    if not candidates:
        return {"parsed_filters": {}, "results": [],
                "answer": "No companies are indexed yet — run POST /embed after enrichment."}

    reranked = _rerank(q, candidates)
    by_id = {c["opportunity_id"]: c for c in candidates}
    results = []
    for item in reranked.get("results", []):
        c = by_id.get(item.get("opportunity_id"), {})
        results.append({
            "opportunity_id": item.get("opportunity_id"),
            "company_name": item.get("company_name") or c.get("company_name", ""),
            "founder_name": c.get("founder_name"),
            "match_reason": item.get("why", ""),
            "relevance": c.get("relevance"),
        })
    return {"parsed_filters": {}, "results": results, "answer": reranked.get("answer", "")}


def _rerank(q: str, candidates: list[dict]) -> dict:
    """LLM reads the retrieved candidate docs and selects/ranks the true matches + an answer."""
    ctx = "\n\n".join(
        f"[{c['opportunity_id']}] {c['company_name']} (relevance {c['relevance']}):\n{(c.get('doc') or '')[:700]}"
        for c in candidates if c.get("opportunity_id"))
    prompt = (f"User query: {q}\n\nCandidate companies retrieved by semantic similarity "
              f"(id, name, knowledge doc):\n\n{ctx}\n\n"
              "Select and rank ONLY the companies that genuinely match the query. For each, give a "
              "one-line reason grounded in its doc. Then write a 1-2 sentence answer. If none fit, "
              "return an empty results list and say so in the answer.")
    return call_structured("query_rerank", RERANK_SCHEMA, prompt,
                           extra_system="Only use opportunity_ids from the candidates provided. "
                                        "Do not invent companies or claims.")
