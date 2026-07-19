"""Central config + client init. Import from here, never re-read env elsewhere."""
import os
from dotenv import load_dotenv

load_dotenv()

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

# When true, 500s return the real error message + traceback tail in the JSON response
# (instead of a generic "Internal Server Error"). Great for fast debugging; turn off for a
# polished demo. Set DEBUG_ERRORS=true in Render while wiring things up.
DEBUG_ERRORS = _flag("DEBUG_ERRORS", False)

# Handelsregister connector backend: fixture (default, safe/demo) | bundesapi | openregister
HANDELSREGISTER_BACKEND = os.getenv("HANDELSREGISTER_BACKEND", "fixture")
HANDELSREGISTER_API_KEY = os.getenv("HANDELSREGISTER_API_KEY", "")

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
