"""Founder Score from public footprint — the cold-start core (Area of Research 3).

Deterministic and transparent on purpose: for pre-track-record founders a glass-box, feature-based
score is more defensible than an LLM guess, and it lets us attach an HONEST uncertainty interval
driven by how much evidence we actually have. Rich footprint -> higher score, narrower interval.
Thin footprint -> score near the prior, WIDE interval, flagged pre-track-record (never penalized
for silence, just reasoned about with low confidence).

Returns score 0-100, interval (±), is_pre_track_record, completeness, and per-driver contributions
(so the number is fully explainable — feeds Agentic Traceability)."""
from __future__ import annotations
import math

PRIOR = 45.0            # neutral starting point before any evidence


def compute(rec: dict, gh: dict | None) -> dict:
    """rec = handelsregister record dict; gh = GithubFootprint.__dict__ or None."""
    score = PRIOR
    drivers: list[str] = []

    def add(pts: float, why: str):
        nonlocal score
        if pts >= 0.5:
            score += pts
            drivers.append(f"{why} (+{pts:.0f})")

    # --- GitHub footprint, weighted by identity match confidence (honest about collisions) ---
    conf = (gh or {}).get("match_confidence", 0) or 0
    if gh and conf >= 0.5:
        stars = gh.get("total_stars", 0) or 0
        followers = gh.get("followers", 0) or 0
        repos = gh.get("public_repos", 0) or 0
        add(min(20, 6 * math.log10(stars + 1)) * conf, f"GitHub {stars} stars")
        add(min(10, 4 * math.log10(followers + 1)) * conf, f"{followers} followers")
        add(min(6, repos * 0.3) * conf, f"{repos} public repos")
        rp = gh.get("recent_push_days_ago")
        if rp is not None and rp <= 90:
            add(6 * conf, f"actively shipping (last push {rp}d)")
        age = gh.get("account_age_days")
        if age and age > 365 * 3:
            add(3 * conf, "long-standing GitHub presence")

    # --- financials from the official register (high signal, already verified) ---
    rev = rec.get("revenue_eur")
    if rev and rev > 0:
        add(min(12, 3 * math.log10(rev + 1)), f"reported revenue EUR {rev:,.0f}")
    emp = rec.get("employees")
    if emp:
        add(min(6, emp * 0.5), f"{emp} employees")

    # --- domain-insight density: a specific, detailed business purpose is a weak positive ---
    purpose = rec.get("business_purpose") or ""
    if len(purpose) > 80:
        add(4, "detailed/specific business purpose")

    score = max(0, min(100, round(score)))

    # --- data completeness -> uncertainty interval (wide when we know little) ---
    have = sum(bool(x) for x in [
        gh and conf >= 0.5,
        rec.get("revenue_eur"), rec.get("employees"),
        rec.get("website"), rec.get("business_purpose"),
        rec.get("github_handle") or rec.get("linkedin_url"),
    ])
    completeness = have / 6.0
    interval = round(32 * (1 - completeness) + 5)          # ~5 (rich) .. ~37 (nothing)

    # pre-track-record: no revenue and no meaningful shipped work
    strong_gh = bool(gh and (gh.get("total_stars", 0) or 0) >= 20)
    is_pre_track_record = not ((rev and rev > 0) or strong_gh)

    if not drivers:
        drivers.append("no public footprint found — scored at prior with wide uncertainty")

    return {
        "score": score,
        "interval": interval,
        "is_pre_track_record": is_pre_track_record,
        "completeness": round(completeness, 2),
        "drivers": drivers,
    }
