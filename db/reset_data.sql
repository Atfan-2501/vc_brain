-- Clean slate for a fresh scan/enrich/score run. Keeps THESES (your fund lens) intact.
-- Why needed: deleting only `companies` orphans `signals` (their dedup_hash survives), so a
-- re-scan would skip everything as "already ingested". Clear the whole data set together.
-- Run in the Supabase SQL editor.

truncate table
  reasoning_log,
  claims,
  founder_score_history,
  outreach,
  opportunities,
  signals,
  companies,
  founders
restart identity cascade;

-- Optional: re-load the demo seed rows (Kessler AI / VaneLabs / NandaHealth with contradictions)
-- by re-running db/seed.sql after this. Skip if you only want live Munich data.
