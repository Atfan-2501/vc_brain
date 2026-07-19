-- Ask the Brain — semantic ranking. Run once in the Supabase SQL editor.
-- Stores a per-company embedding as jsonb (no pgvector needed; ranking is done in-process).
alter table companies add column if not exists embedding jsonb;
