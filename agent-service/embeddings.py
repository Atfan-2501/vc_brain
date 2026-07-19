"""Semantic embeddings for Ask the Brain. Precompute one embedding per company (name + sector +
geography + business purpose), store it as jsonb, and at query time embed the query and rank by
cosine similarity. No pgvector required — at demo scale a Python cosine over the candidate set is
instant, and jsonb storage keeps the schema change to a single column.

Backfill is deliberate (POST /embed), like enrichment, so it doesn't silently spend OpenAI."""
from __future__ import annotations
import math

import config

EMBED_MODEL = "text-embedding-3-small"      # 1536-dim, cheap


def embed_text(text: str) -> list[float]:
    r = config.openai_client().embeddings.create(model=EMBED_MODEL, input=text[:8000])
    return r.data[0].embedding


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def embed_all(limit: int | None = None, force: bool = False) -> dict:
    """Backfill embeddings. force=True re-embeds every company (run after enrichment so founder
    claims are included); otherwise only companies without an embedding."""
    import db
    ids = db.companies_needing_embedding(limit, force=force)
    done = 0
    for cid in ids:
        doc = db.build_company_doc(cid)
        if not doc.strip():
            continue
        try:
            db.set_company_embedding(cid, embed_text(doc), doc)   # store the doc for RAG re-rank
            done += 1
        except Exception:
            continue
    return {"embedded": done, "candidates": len(ids)}
