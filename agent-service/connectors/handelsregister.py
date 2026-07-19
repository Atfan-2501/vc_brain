"""Handelsregister connector — discovers newly-formed Munich companies (GmbHs) as an
outbound sourcing stream. A brand-new GmbH is the earliest possible founder signal:
it exists before funding, before GitHub traction, before press. That's the challenge's
"discover before the first round" mandate, made concrete for Munich.

BACKENDS (config.HANDELSREGISTER_BACKEND):
- "fixture"  (default): reads connectors/fixtures/munich_gmbh.json. Safe, instant, demo-proof.
- "bundesapi": live scrape of the official portal via the bundesAPI/handelsregister package.
               RATE-LIMITED to <60 requests/hour by law (portal cites StGB 303a/b). Opt-in.
- "openregister": third-party REST API (needs HANDELSREGISTER_API_KEY). Cleanest live data.

The official free portal is SEARCH-based (no "new registrations" feed), so we search Munich
GmbHs by sector keywords and use the registration date as the freshness signal.

Output: normalized HandelsregisterRecord objects, plus mappers to the signals/founders/
companies row shapes so sourcing.py can push them through the same funnel as inbound.
"""
from __future__ import annotations

import json
import os
import time
import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path

import config

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "munich_gmbh.json"

# Munich postal codes are 80331-81929; the register court is "München".
MUNICH_PLZ_PREFIXES = ("80", "81")

# Rough sector inference from the German business purpose (Unternehmensgegenstand).
# Keyed to your thesis sectors so outbound records screen through the same lens as inbound.
_SECTOR_KEYWORDS = {
    "AI infra": ["ki-inferenz", "machine-learning", "neuromorph", "edge-ki", "recheninfrastruktur",
                 "ki-modelle", "ki-gestuetzt", "ki-gestützt"],
    "devtools": ["entwicklerwerkzeug", "continuous-integration", "developer", "devtools",
                 "open-source"],
    "fintech": ["zahlungsabwicklung", "embedded finance", "finanzdienstleistung", "fintech"],
    "robotics": ["roboter", "robotics", "intralogistik"],
    "biotech": ["wirkstoffforschung", "molekuel", "molekül", "bio"],
    "energy": ["stromnetz", "energiemanagement", "energy"],
}


@dataclass
class HandelsregisterRecord:
    company_name: str
    register_court: str
    register_type: str          # HRB, HRA, ...
    register_number: str
    legal_form: str
    city: str
    postal_code: str
    street: str
    managing_directors: list[str]
    business_purpose: str
    registered_on: str          # ISO date
    source_url: str
    # --- rich fields from the OpenRegister detail call (Tier-0 enrichment; already paid for) ---
    website: str | None = None
    github_handle: str | None = None
    linkedin_url: str | None = None
    twitter_handle: str | None = None
    revenue_eur: float | None = None      # latest reported, converted from cents
    employees: int | None = None
    net_income_eur: float | None = None
    industry_codes: list[str] | None = None

    @property
    def register_id(self) -> str:
        return f"{self.register_court} {self.register_type} {self.register_number}"

    @property
    def citation(self) -> str:
        """Canonical, verifiable citation for a company: its register ID. Anyone can confirm it
        by searching handelsregister.de. No fabricated deep link."""
        return f"Handelsregister {self.register_id}"

    @property
    def inferred_sector(self) -> str | None:
        text = self.business_purpose.lower()
        for sector, kws in _SECTOR_KEYWORDS.items():
            if any(k in text for k in kws):
                return sector
        return None

    @property
    def days_since_registration(self) -> int | None:
        try:
            d = datetime.fromisoformat(self.registered_on).date()
            return (datetime.now(timezone.utc).date() - d).days
        except Exception:
            return None


# ---------------- rate limiting (protects the live backends) ----------------
_REQUEST_TIMES: list[float] = []
RATE_LIMIT_PER_HOUR = 55          # stay safely under the legal 60/hour cap


def _rate_limit_guard():
    now = time.time()
    _REQUEST_TIMES[:] = [t for t in _REQUEST_TIMES if now - t < 3600]
    if len(_REQUEST_TIMES) >= RATE_LIMIT_PER_HOUR:
        wait = 3600 - (now - _REQUEST_TIMES[0])
        raise RuntimeError(
            f"Handelsregister hourly rate limit reached ({RATE_LIMIT_PER_HOUR}/h). "
            f"Retry in {int(wait)}s. Never exceed 60/h — the portal enforces it legally.")
    _REQUEST_TIMES.append(now)


# ---------------- backends ----------------
def _fixture_records() -> list[HandelsregisterRecord]:
    data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return [HandelsregisterRecord(**r) for r in data]


def _bundesapi_records(keywords: str) -> list[HandelsregisterRecord]:
    """Live scrape via the bundesAPI/handelsregister package. Opt-in.
    Install: pip install handelsregister  (or vendor the repo). Respects the rate limit.
    NOTE: the portal search returns company + register data; managing directors and full
    business purpose may require a second document fetch — kept minimal here to stay under
    the rate cap. Prefer 'openregister' for richer structured data."""
    _rate_limit_guard()
    try:
        from handelsregister import HandelsregisterAPI  # type: ignore
    except ImportError as e:
        raise RuntimeError("bundesapi backend needs the 'handelsregister' package. "
                           "pip install handelsregister — or use backend='fixture'.") from e
    api = HandelsregisterAPI()
    raw = api.search(keywords=keywords)          # interface per bundesAPI/handelsregister
    out: list[HandelsregisterRecord] = []
    for r in raw or []:
        out.append(HandelsregisterRecord(
            company_name=r.get("name", ""), register_court=r.get("court", "München"),
            register_type=r.get("register_type", "HRB"), register_number=r.get("register_number", ""),
            legal_form=r.get("legal_form", "GmbH"), city=r.get("city", "München"),
            postal_code=r.get("postal_code", ""), street=r.get("street", ""),
            managing_directors=r.get("managing_directors", []),
            business_purpose=r.get("purpose", ""), registered_on=r.get("registered_on", ""),
            source_url="https://www.handelsregister.de/rp_web/"))
    return out


_OR_BASE = "https://api.openregister.de"


def _or_request(method: str, path: str, key: str, body: dict | None = None) -> dict:
    import urllib.request, urllib.error
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"{_OR_BASE}{path}", data=data, method=method,
                                 headers={"Authorization": f"Bearer {key}",
                                          "Content-Type": "application/json",
                                          "Accept": "application/json",
                                          # Cloudflare blocks the default Python-urllib UA (err 1010)
                                          "User-Agent": "vc-brain/1.0 (+https://openregister.de)"})
    # NOTE: no _rate_limit_guard here — that 55/h cap is the LEGAL limit for scraping the
    # handelsregister.de portal (bundesapi backend). OpenRegister is a paid API, credit-limited,
    # with its own 429 handling, so it must not be throttled by the portal rule.
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        # surface OpenRegister's actual JSON error message, not a bare status code
        detail = e.read().decode(errors="replace")
        raise RuntimeError(f"OpenRegister {method} {path} -> HTTP {e.code}: {detail}") from None


def _openregister_records(keywords: str) -> list[HandelsregisterRecord]:
    """Real data via openregister.de. Needs config.OPENREGISTER_API_KEY (free tier: 50 credits/mo).
    Flow: 1 search (10 credits) -> client-side keep GmbHs -> up to OPENREGISTER_MAX_DETAILS
    detail calls (10 credits each) for directors + purpose + incorporation date.
    Verified against the OpenRegister OpenAPI schema (CompanyV1)."""
    import sys
    key = config.OPENREGISTER_API_KEY
    if not key:
        raise RuntimeError("openregister backend needs OPENREGISTER_API_KEY.")

    # 1) search Munich GmbHs. City goes in the `filters` array (NOT `location`, which is lat/lon).
    filters = [
        {"field": "city", "value": "München"},
        {"field": "legal_form", "value": "gmbh"},
        {"field": "active", "value": "true"},
    ]
    if config.OPENREGISTER_MIN_INCORPORATED:                 # optional: newly-founded only
        filters.append({"field": "incorporated_at", "min": config.OPENREGISTER_MIN_INCORPORATED})
    search = _or_request("POST", "/v1/search/company", key,
                         {"filters": filters, "pagination": {"page": 1, "per_page": 50}})
    results = search.get("results", [])
    if config.OPENREGISTER_DEBUG:
        print(f"[openregister] raw search results: {len(results)}; "
              f"total={search.get('pagination', {}).get('total_results')}", file=sys.stderr)
    stubs = [s for s in results
             if s.get("legal_form") == "gmbh" and s.get("active", True)]
    stubs = stubs[:config.OPENREGISTER_MAX_RESULTS]

    out: list[HandelsregisterRecord] = []
    for i, stub in enumerate(stubs):
        cid = stub.get("company_id")
        # spend a detail credit only on the first N; the rest are kept lean and enriched later
        if cid and i < config.OPENREGISTER_MAX_DETAILS:
            try:
                c = _or_request("GET", f"/v1/company/{cid}", key)
                out.append(_or_map_company(c, stub))
                continue
            except Exception:
                pass                                   # fall through to lean on any detail error
        out.append(_or_map_stub(stub))
    if config.OPENREGISTER_DEBUG:
        detailed = sum(1 for r in out if r.managing_directors)
        print(f"[openregister] kept {len(out)} companies ({detailed} with full detail, "
              f"{len(out) - detailed} lean/to-enrich)", file=sys.stderr)
    return out


def _or_map_stub(stub: dict) -> HandelsregisterRecord:
    """Lean record from a search hit only (no detail credit spent). Directors + purpose are
    empty and get filled by the enrichment step."""
    return HandelsregisterRecord(
        company_name=stub.get("name", ""),
        register_court=stub.get("register_court", "München"),
        register_type=stub.get("register_type", "HRB"),
        register_number=stub.get("register_number", ""),
        legal_form=stub.get("legal_form", "gmbh"),
        city="München", postal_code="", street="",
        managing_directors=[], business_purpose="", registered_on="",
        source_url=f"https://openregister.de/company/{stub.get('company_id', '')}")


def _or_map_company(c: dict, stub: dict) -> HandelsregisterRecord:
    """Map the OpenRegister CompanyV1 detail object into our record shape."""
    reg = c.get("register") or {}
    addr = c.get("address") or {}
    purpose = (c.get("purpose") or {}).get("purpose", "") if c.get("purpose") else ""
    directors = []
    for rep in c.get("representation") or []:
        if rep.get("role") == "DIRECTOR" and rep.get("type") == "natural_person":
            np = rep.get("natural_person") or {}
            name = " ".join(x for x in [np.get("first_name"), np.get("last_name")] if x) \
                   or rep.get("name")
            if name:
                directors.append(name)
    name = (c.get("name") or {}).get("name") if isinstance(c.get("name"), dict) else stub.get("name", "")
    # contact: website + social handles (feed Tier-1 GitHub + founder footprint)
    contact = c.get("contact") or {}
    social = (contact.get("social_media") or {}) if contact else {}
    # indicators: latest-first array of financials (values in CENTS -> convert to EUR)
    ind = (c.get("indicators") or [{}])[0] if c.get("indicators") else {}
    cents = lambda v: (v / 100.0) if isinstance(v, (int, float)) else None
    codes = [x.get("code") for x in (c.get("industry_codes", {}).get("WZ2025") or [])
             if x.get("code")]
    return HandelsregisterRecord(
        company_name=name or stub.get("name", ""),
        register_court=reg.get("register_court", stub.get("register_court", "München")),
        register_type=reg.get("register_type", stub.get("register_type", "HRB")),
        register_number=reg.get("register_number", stub.get("register_number", "")),
        legal_form=c.get("legal_form", "gmbh"),
        city=addr.get("city", "München"),
        postal_code=addr.get("postal_code", ""),
        street=addr.get("street", ""),
        managing_directors=directors,
        business_purpose=purpose,
        registered_on=c.get("incorporated_at", ""),
        source_url=f"https://openregister.de/company/{c.get('id', '')}",
        website=contact.get("website_url"),
        github_handle=social.get("github"),
        linkedin_url=social.get("linkedin"),
        twitter_handle=social.get("twitter"),
        revenue_eur=cents(ind.get("revenue")),
        employees=ind.get("employees"),
        net_income_eur=cents(ind.get("net_income")),
        industry_codes=codes or None)


# ---------------- public entry point ----------------
def search_munich(keywords: str = "", max_age_days: int | None = None,
                  sectors: list[str] | None = None) -> list[HandelsregisterRecord]:
    """Return Munich GmbH records, newest-first, filtered to Munich + optional freshness/sector.
    keywords steer the live search; the fixture backend ignores them (returns all, then filters)."""
    backend = config.HANDELSREGISTER_BACKEND
    if backend == "fixture":
        records = _fixture_records()
    elif backend == "bundesapi":
        records = _bundesapi_records(keywords or "GmbH München")
    elif backend == "openregister":
        records = _openregister_records(keywords or "")
    else:
        raise ValueError(f"unknown HANDELSREGISTER_BACKEND: {backend}")

    # keep Munich only (defensive — live search can leak nearby towns). Lenient: match the
    # court/city text or an 80/81 postal code, so lean records (no postal code) aren't dropped.
    def _is_munich(r):
        return ("münchen" in (r.register_court or "").lower()
                or "münchen" in (r.city or "").lower()
                or (r.postal_code[:2] in MUNICH_PLZ_PREFIXES if r.postal_code else False))
    records = [r for r in records if _is_munich(r)]
    if max_age_days is not None:
        records = [r for r in records
                   if (r.days_since_registration or 10**6) <= max_age_days]
    if sectors:
        records = [r for r in records if r.inferred_sector in sectors]
    records.sort(key=lambda r: r.registered_on, reverse=True)   # newest first
    return records


# ---------------- mappers to DB row shapes (consumed by sourcing.py) ----------------
def to_signal_row(r: HandelsregisterRecord) -> dict:
    dedup = hashlib.sha256(r.register_id.encode()).hexdigest()[:32]
    raw = asdict(r)
    raw["register_id"] = r.register_id          # canonical citation (court + type + number)
    raw["citation"] = r.citation
    return {
        "source": "handelsregister",
        "source_url": r.source_url,              # official portal (search-based, no deep links)
        "raw_content": json.dumps(raw, ensure_ascii=False),
        "tags": ["outbound", "handelsregister", "munich",
                 *( [r.inferred_sector] if r.inferred_sector else [] )],
        "dedup_hash": f"handelsregister:{dedup}",
        "extracted_at": datetime.now(timezone.utc).isoformat(),
    }


def to_company_row(r: HandelsregisterRecord) -> dict:
    return {
        "name": r.company_name, "sector": r.inferred_sector,
        "geography": "Munich, DE", "stage": "pre-seed",
    }


def to_founder_rows(r: HandelsregisterRecord) -> list[dict]:
    """One founder per managing director. Fresh formation -> pre_track_record until other
    signals (GitHub, launches) resolve to the same person."""
    return [{"name": name, "domain": None, "is_pre_track_record": True}
            for name in r.managing_directors]
