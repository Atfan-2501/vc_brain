"""Outbound Scanner — the 30% differentiator. H6-H9.
Two Tavily jobs (Show HN + ProductHunt) -> signals -> SAME scoring funnel as inbound.
Detected founders become opportunities with source='outbound'. Both funnels converge."""
import uuid
import config

CHANNEL_QUERIES = {
    "show_hn": "Show HN launches this week AI infra devtools startups site:news.ycombinator.com",
    "producthunt": "ProductHunt top launches this week developer tools AI",
    # add arxiv / hackathon winners later if time
}


def run_scan(channels: list[str]) -> str:
    scan_id = str(uuid.uuid4())
    tv = config.tavily_client()
    for ch in channels:
        q = CHANNEL_QUERIES.get(ch)
        if not q:
            continue
        results = tv.search(query=q, max_results=8, search_depth="advanced")
        for r in results.get("results", []):
            _ingest_signal(source=ch, url=r["url"], raw=r["content"], title=r["title"])
    return scan_id


def _ingest_signal(source, url, raw, title):
    """Dedup on (source, url) hash, resolve/create founder, insert signal, then run it
    through the same pipeline as inbound so it appears as an outbound opportunity.
    TODO: implement dedup + identity resolution + funnel handoff. H6-H9."""
    raise NotImplementedError("wire in H6-H9")
