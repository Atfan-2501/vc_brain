-- Ask the Brain (RAG) — semantic retrieval. Run once in the Supabase SQL editor.
-- Stores a per-company embedding (jsonb) + the source document it was built from (for LLM
-- re-ranking and transparency). No pgvector needed; ranking is done in-process at demo scale.
alter table companies add column if not exists embedding jsonb;
alter table companies add column if not exists embedding_doc text;
