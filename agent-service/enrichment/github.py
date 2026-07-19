"""Tier-1 enrichment: GitHub footprint. The strongest FREE cold-start signal for a technical
founder — shipped work and execution velocity that exist before any funding.

Resolve a founder to a GitHub account (by known handle, else name+Munich search), then compute
footprint features. Everything returns with a `match_confidence` so downstream Trust Scores stay
honest about name-collision risk. No token needed for low volume; set GITHUB_TOKEN to raise the
rate limit (60/h anon -> 5000/h authed)."""
from __future__ import annotations

import os
import json
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone
from dataclasses import dataclass, field

GITHUB_API = "https://api.github.com"


@dataclass
class GithubFootprint:
    login: str
    profile_url: str
    match_confidence: float          # 0-1: how sure we are this is the right person
    name: str | None = None
    company: str | None = None
    location: str | None = None
    followers: int = 0
    public_repos: int = 0
    account_age_days: int | None = None
    total_stars: int = 0             # summed across owned repos
    top_languages: list[str] = field(default_factory=list)
    recent_push_days_ago: int | None = None   # freshness of latest push
    notable_repos: list[dict] = field(default_factory=list)  # [{name, stars, url, lang}]


def _get(path: str, params: dict | None = None) -> dict | list | None:
    url = f"{GITHUB_API}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "vc-brain/1.0"}
    token = os.getenv("GITHUB_TOKEN", "")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        if e.code in (403, 429):
            raise RuntimeError("GitHub rate limit hit — set GITHUB_TOKEN for 5000/h.") from None
        return None
    except Exception:
        return None


def resolve(founder_name: str, known_handle: str | None = None,
            location_hint: str = "Munich") -> GithubFootprint | None:
    """Find the founder's GitHub account. Known handle -> high confidence; name search -> lower."""
    if known_handle:
        handle = known_handle.rsplit("/", 1)[-1].strip("@/")
        user = _get(f"/users/{handle}")
        if user and user.get("type") == "User":
            return _build(user, match_confidence=0.9)   # handed to us by the register/website

    # fall back to a name + location search
    q = f"{founder_name} location:{location_hint}"
    res = _get("/search/users", {"q": q, "per_page": 5})
    items = (res or {}).get("items", []) if isinstance(res, dict) else []
    for it in items:
        user = _get(f"/users/{it['login']}")
        if not user:
            continue
        conf = _name_match_confidence(founder_name, user)
        if conf >= 0.5:                                 # only accept a plausible match
            return _build(user, match_confidence=conf)
    return None


def _name_match_confidence(founder_name: str, user: dict) -> float:
    """Cheap heuristic: full-name match + Munich location raises confidence; bare login match low."""
    fn = founder_name.lower().strip()
    gh_name = (user.get("name") or "").lower().strip()
    loc = (user.get("location") or "").lower()
    conf = 0.3
    if gh_name and gh_name == fn:
        conf = 0.75
    elif gh_name and all(p in gh_name for p in fn.split()):
        conf = 0.6
    if "münchen" in loc or "munich" in loc:
        conf += 0.15
    return min(conf, 0.9)                               # name-only never reaches "certain"


def _build(user: dict, match_confidence: float) -> GithubFootprint:
    repos = _get(f"/users/{user['login']}/repos",
                 {"per_page": 100, "sort": "pushed"}) or []
    owned = [r for r in repos if not r.get("fork")]
    total_stars = sum(r.get("stargazers_count", 0) for r in owned)
    langs: dict[str, int] = {}
    for r in owned:
        if r.get("language"):
            langs[r["language"]] = langs.get(r["language"], 0) + 1
    top_languages = [l for l, _ in sorted(langs.items(), key=lambda x: -x[1])[:5]]
    notable = sorted(owned, key=lambda r: r.get("stargazers_count", 0), reverse=True)[:5]
    notable_repos = [{"name": r["name"], "stars": r.get("stargazers_count", 0),
                      "url": r.get("html_url"), "lang": r.get("language")} for r in notable]

    def _days_since(iso: str | None):
        if not iso:
            return None
        try:
            d = datetime.fromisoformat(iso.replace("Z", "+00:00"))
            return (datetime.now(timezone.utc) - d).days
        except Exception:
            return None

    recent_push = min((_days_since(r.get("pushed_at")) for r in owned
                       if _days_since(r.get("pushed_at")) is not None), default=None)
    return GithubFootprint(
        login=user["login"], profile_url=user.get("html_url", ""),
        match_confidence=round(match_confidence, 2),
        name=user.get("name"), company=user.get("company"), location=user.get("location"),
        followers=user.get("followers", 0), public_repos=user.get("public_repos", 0),
        account_age_days=_days_since(user.get("created_at")),
        total_stars=total_stars, top_languages=top_languages,
        recent_push_days_ago=recent_push, notable_repos=notable_repos)


def to_signal_row(founder_id, fp: GithubFootprint) -> dict:
    """A GitHub footprint stored as a signal (never discarded, feeds Founder Score)."""
    return {
        "founder_id": founder_id, "source": "github", "source_url": fp.profile_url,
        "raw_content": json.dumps(fp.__dict__, ensure_ascii=False),
        "tags": ["enrichment", "github", "footprint"],
        "dedup_hash": f"github:{fp.login}",
        "extracted_at": datetime.now(timezone.utc).isoformat(),
    }
