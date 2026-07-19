"""Outbound Scanner — the 30% differentiator. H6-H9.
Channels -> signals -> SAME scoring funnel as inbound. Detected founders become
opportunities with source='outbound'. Both funnels converge.

Channels:
- handelsregister : newly-formed Munich GmbHs (earliest pre-funding signal). No Tavily.
- show_hn         : Show HN launches via Tavily.
- producthunt     : ProductHunt launches via Tavily.
"""
import uuid
import config

CHANNEL_QUERIES = {   # Tavily-backed channels
    "show_hn": "Show HN launches this week AI infra devtools startups Munich site:news.ycombinator.com",
    "producthunt": "ProductHunt top launches this week developer tools AI Munich",
}


def run_scan(channels: list[str]) -> str:
    scan_id = str(uuid.uuid4())
    for ch in channels:
        if ch == "handelsregister":
            scan_handelsregister()
        elif ch in CHANNEL_QUERIES:
            _scan_tavily(ch)
    return scan_id


# ---------------- Handelsregister channel ----------------
def scan_handelsregister(max_age_days: int = 180, sectors: list[str] | None = None) -> int:
    """Discover recent Munich GmbHs and push each through the funnel. Returns count ingested.
    Newest-first; filter by freshness and (optionally) the active thesis sectors."""
    from connectors import handelsregister as hr
    records = hr.search_munich(max_age_days=max_age_days, sectors=sectors)
    ingested = 0
    for r in records:
        if _persist_record(r):
            ingested += 1
    return ingested


def _persist_record(r) -> bool:
    """signal -> company -> founder(s) -> outbound opportunity. Returns False if deduped."""
    import db
    from connectors import handelsregister as hr

    signal_id = db.insert_signal(hr.to_signal_row(r))   # dedups on dedup_hash
    if signal_id is None:
        return False                                    # already discovered before
    company_id = db.insert_company(hr.to_company_row(r))
    founder_id = None
    for f in hr.to_founder_rows(r):
        founder_id = db.upsert_founder_by_name(f)       # identity resolution across sources
        db.link_signal(signal_id, founder_id, company_id)
    # create an outbound opportunity so it appears on the board and gets scored like inbound
    db.create_outbound_opportunity(company_id=company_id, founder_id=founder_id,
                                   first_signal_at=r.registered_on)
    return True


# ---------------- Tavily channels ----------------
def _scan_tavily(channel: str):
    q = CHANNEL_QUERIES.get(channel)
    if not q:
        return
    results = config.tavily_client().search(query=q, max_results=8, search_depth="advanced")
    for r in results.get("results", []):
        _ingest_web_signal(source=channel, url=r["url"], raw=r["content"], title=r["title"])


def _ingest_web_signal(source, url, raw, title):
    """Dedup on (source, url), resolve/create founder, insert signal, then funnel.
    TODO: implement web-signal identity resolution + funnel handoff. H6-H9."""
    raise NotImplementedError("wire in H6-H9")


# ---------------- preview (no DB) — used for local/offline testing ----------------
def preview_handelsregister(max_age_days: int | None = None, sectors=None) -> list[dict]:
    """Return normalized rows WITHOUT touching the DB. Lets you eyeball the connector
    output before wiring persistence / with USE_STUBS on."""
    from connectors import handelsregister as hr
    out = []
    for r in hr.search_munich(max_age_days=max_age_days, sectors=sectors):
        out.append({
            "signal": hr.to_signal_row(r),
            "company": hr.to_company_row(r),
            "founders": hr.to_founder_rows(r),
            "register_id": r.register_id,
            "sector": r.inferred_sector,
            "days_old": r.days_since_registration,
        })
    return out
