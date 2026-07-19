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

    @property
    def register_id(self) -> str:
        return f"{self.register_court} {self.register_type} {self.register_number}"

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


def _openregister_records(keywords: str) -> list[HandelsregisterRecord]:
    """Third-party REST API (openregister.de). Needs config.HANDELSREGISTER_API_KEY."""
    _rate_limit_guard()
    import urllib.request, urllib.parse
    key = os.getenv("HANDELSREGISTER_API_KEY", "")
    if not key:
        raise RuntimeError("openregister backend needs HANDELSREGISTER_API_KEY.")
    params = urllib.parse.urlencode({"q": keywords, "city": "München", "legal_form": "GmbH"})
    req = urllib.request.Request(f"https://api.openregister.de/v1/search?{params}",
                                 headers={"Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        payload = json.loads(resp.read())
    out = []
    for r in payload.get("companies", []):
        out.append(HandelsregisterRecord(
            company_name=r.get("name", ""), register_court=r.get("register_court", "München"),
            register_type=r.get("register_type", "HRB"), register_number=r.get("register_number", ""),
            legal_form=r.get("legal_form", "GmbH"), city=r.get("city", "München"),
            postal_code=r.get("postal_code", ""), street=r.get("address", ""),
            managing_directors=[d.get("name") for d in r.get("management", [])],
            business_purpose=r.get("purpose", ""), registered_on=r.get("registered_on", ""),
            source_url=r.get("source_url", "https://openregister.de")))
    return out


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

    # keep Munich only (defensive — live search can leak nearby towns)
    records = [r for r in records
               if r.register_court == "München" or r.postal_code[:2] in MUNICH_PLZ_PREFIXES]
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
    return {
        "source": "handelsregister",
        "source_url": r.source_url,
        "raw_content": json.dumps(asdict(r), ensure_ascii=False),
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
