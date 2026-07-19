"""Central config + client init. Import from here, never re-read env elsewhere."""
import os

# python-dotenv is only a convenience for loading a local .env file. It's optional:
# on Render (and for the stdlib-only harvest script) env vars are already set, so a missing
# dotenv must not crash the import.
try:
    from dotenv import load_dotenv
    load_dotenv()
except ModuleNotFoundError:
    pass

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
AGENT_SERVICE_URL = os.getenv("AGENT_SERVICE_URL", "http://localhost:8000")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

# Master stub switch. When true, endpoints return canned demo JSON (H0 integration test).
USE_STUBS = os.getenv("USE_STUBS", "true").lower() == "true"


def _flag(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).lower() == "true"


# Granular capability flags — each defaults to the inverse of USE_STUBS but can be flipped
# independently. This lets you turn on the DB + outbound scanning NOW while keeping the
# not-yet-built pipeline agents stubbed. Set these in Render's Environment.
#   DB_WIRED   -> reads/writes real Supabase (/opportunities, detail, /founders, /reasoning-log,
#                 /thesis) and lets /scan persist discovered founders.
#   APPLY_LIVE -> /apply runs the real extraction->...->memo pipeline (needs the agents built).
#   QUERY_LIVE -> /query calls OpenAI to parse compound queries.
DB_WIRED   = _flag("DB_WIRED", not USE_STUBS)
APPLY_LIVE = _flag("APPLY_LIVE", not USE_STUBS)
QUERY_LIVE = _flag("QUERY_LIVE", not USE_STUBS)
#   SCORING_LIVE -> /score runs the 3-axis OpenAI scorer (needs OPENAI_API_KEY + DB_WIRED).
SCORING_LIVE = _flag("SCORING_LIVE", not USE_STUBS)
#   WEB_ENRICH -> enrichment Tier 2: Tavily web search + OpenAI claim extraction (needs both keys).
WEB_ENRICH = _flag("WEB_ENRICH", not USE_STUBS)
#   MEMO_LIVE -> /memo runs the Memo Agent (OpenAI): 5-section memo + decision (needs OPENAI + DB).
MEMO_LIVE = _flag("MEMO_LIVE", not USE_STUBS)
#   SCREEN_GATES -> a failed thesis screen STOPS full analysis (axes+memo). False = advisory only.
SCREEN_GATES = _flag("SCREEN_GATES", True)

# When true, 500s return the real error message + traceback tail in the JSON response
# (instead of a generic "Internal Server Error"). Great for fast debugging; turn off for a
# polished demo. Set DEBUG_ERRORS=true in Render while wiring things up.
DEBUG_ERRORS = _flag("DEBUG_ERRORS", False)

# Handelsregister connector backend: fixture (default, safe/demo) | bundesapi | openregister
HANDELSREGISTER_BACKEND = os.getenv("HANDELSREGISTER_BACKEND", "fixture")
OPENREGISTER_API_KEY = os.getenv("OPENREGISTER_API_KEY", "")
# total companies to keep from ONE search (10 credits, up to 50 lean records — cheap).
OPENREGISTER_MAX_RESULTS = int(os.getenv("OPENREGISTER_MAX_RESULTS", "20"))
# of those, how many get a full-detail call (directors/purpose/date) at 10 credits EACH.
# free tier = 50 credits/mo, so 10 (search) + 4*10 = 50. Raise on a paid plan. The rest are
# kept as lean records (name + register id) and filled in by the enrichment step.
OPENREGISTER_MAX_DETAILS = int(os.getenv("OPENREGISTER_MAX_DETAILS", "4"))
# how many search pages to walk (each = 10 credits) when gathering non-shell candidates.
OPENREGISTER_MAX_PAGES = int(os.getenv("OPENREGISTER_MAX_PAGES", "6"))
# optional recency filter (DD-MM-YYYY). Only return companies incorporated on/after this date,
# to bias toward newly-founded startups. Empty = no recency filter (safest for non-empty results).
OPENREGISTER_MIN_INCORPORATED = os.getenv("OPENREGISTER_MIN_INCORPORATED", "")
OPENREGISTER_DEBUG = _flag("OPENREGISTER_DEBUG", False)
# drop shelf companies (Vorratsgesellschaften) from scan results — they're not real startups
HANDELSREGISTER_EXCLUDE_SHELF = _flag("HANDELSREGISTER_EXCLUDE_SHELF", True)

# Per-agent override: flip one agent live while others stay stubbed during H1-H6.
# e.g. STUB_AGENTS = {"extraction": False} makes only extraction call OpenAI for real.
STUB_AGENTS = {
    "extraction": USE_STUBS,
    "verification": USE_STUBS,
    "screener": USE_STUBS,
    "axis_scorer": USE_STUBS,
    "founder_score": USE_STUBS,
    "memo": USE_STUBS,
    "query": USE_STUBS,
    "sourcing": USE_STUBS,
}

# --- lazy clients (only built when a real agent needs them) ---
_openai = _tavily = _supabase = None

def openai_client():
    global _openai
    if _openai is None:
        from openai import OpenAI
        _openai = OpenAI(api_key=OPENAI_API_KEY)
    return _openai

def tavily_client():
    global _tavily
    if _tavily is None:
        from tavily import TavilyClient
        _tavily = TavilyClient(api_key=TAVILY_API_KEY)
    return _tavily

def supabase_client():
    global _supabase
    if _supabase is None:
        from supabase import create_client
        _supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    return _supabase
