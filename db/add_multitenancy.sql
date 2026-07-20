-- Multi-tenancy: scope all data to the owning user. Run once in the Supabase SQL editor.
-- owner_id = the Supabase auth user id (uuid) that created the row.
alter table theses          add column if not exists owner_id uuid;
alter table founders        add column if not exists owner_id uuid;
alter table companies       add column if not exists owner_id uuid;
alter table signals         add column if not exists owner_id uuid;
alter table claims          add column if not exists owner_id uuid;
alter table opportunities   add column if not exists owner_id uuid;
alter table reasoning_log   add column if not exists owner_id uuid;

create index if not exists idx_opps_owner    on opportunities(owner_id);
create index if not exists idx_founders_owner on founders(owner_id);
create index if not exists idx_companies_owner on companies(owner_id);
create index if not exists idx_signals_owner  on signals(owner_id);
create index if not exists idx_theses_owner   on theses(owner_id);

-- signal dedup is now PER OWNER (two users can discover the same founder independently)
alter table signals drop constraint if exists signals_dedup_hash_key;
create unique index if not exists uq_signals_owner_dedup on signals(owner_id, dedup_hash);
