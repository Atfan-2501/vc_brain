-- ============================================================
-- VC Brain — Supabase / Postgres schema (Memory layer)
-- Run in Supabase SQL editor. Order matters (FKs).
-- ============================================================

create extension if not exists "pgcrypto";           -- gen_random_uuid()

-- ---------- THESES: the fund lens ----------
create table theses (
  thesis_id        uuid primary key default gen_random_uuid(),
  sectors          text[]  not null default '{}',
  stages           text[]  not null default '{}',
  geographies      text[]  not null default '{}',
  check_size_usd   integer not null default 100000,
  ownership_target_pct numeric,
  risk_appetite    text check (risk_appetite in ('low','medium','high')),
  active           boolean not null default true,
  created_at       timestamptz not null default now()
);

-- ---------- FOUNDERS: persistent, follow the person ----------
create table founders (
  founder_id       uuid primary key default gen_random_uuid(),
  name             text not null,
  github_handle    text,
  linkedin_slug    text,
  twitter_handle   text,
  domain           text,
  -- persistent Founder Score, NEVER reset
  founder_score          numeric,           -- 0-100
  founder_score_interval numeric,           -- ± uncertainty
  is_pre_track_record    boolean not null default false,
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now()
);

-- timestamped history so the UI shows the TREND, not just the latest number
create table founder_score_history (
  id               uuid primary key default gen_random_uuid(),
  founder_id       uuid not null references founders(founder_id) on delete cascade,
  score            numeric not null,
  interval         numeric,
  trigger_signal_id uuid,                    -- what caused the recompute
  at               timestamptz not null default now()
);

-- ---------- COMPANIES: a founder can appear across many ----------
create table companies (
  company_id       uuid primary key default gen_random_uuid(),
  name             text not null,
  founder_id       uuid references founders(founder_id) on delete set null,
  sector           text,
  geography        text,
  stage            text,
  created_at       timestamptz not null default now()
);

-- ---------- SIGNALS: every raw ingested item. Nothing is deleted ----------
create table signals (
  signal_id        uuid primary key default gen_random_uuid(),
  founder_id       uuid references founders(founder_id) on delete set null,
  company_id       uuid references companies(company_id) on delete set null,
  source           text not null,           -- github | producthunt | show_hn | arxiv | deck | social
  source_url       text,
  raw_content      text,
  tags             text[] not null default '{}',
  dedup_hash       text unique,             -- hash(normalized source + external_id)
  extracted_at     timestamptz,
  ingested_at      timestamptz not null default now()
);

-- ---------- CLAIMS: atomic assertions + per-claim Trust Score ----------
create table claims (
  claim_id         uuid primary key default gen_random_uuid(),
  company_id       uuid references companies(company_id) on delete cascade,
  source_signal_id uuid references signals(signal_id) on delete set null,
  claim_text       text not null,
  claim_type       text,                    -- traction | team | market | tech | financial
  trust_score      numeric check (trust_score >= 0 and trust_score <= 1),
  verification_status text not null default 'unverified'
                     check (verification_status in ('verified','unverified','contradicted')),
  verification_evidence_url text,
  contradiction_note text,
  source_ref       jsonb,                    -- {type:'deck', slide_number:7} or {type:'web', url:...}
  created_at       timestamptz not null default now()
);

-- ---------- OPPORTUNITIES: one per (company, application/detection) ----------
create table opportunities (
  opportunity_id   uuid primary key default gen_random_uuid(),
  company_id       uuid not null references companies(company_id) on delete cascade,
  founder_id       uuid references founders(founder_id) on delete set null,
  thesis_id        uuid references theses(thesis_id) on delete set null,
  source           text not null default 'inbound',  -- inbound | outbound
  stage            text not null default 'sourcing'  -- sourcing | screening | diligence | decision
                     check (stage in ('sourcing','screening','diligence','decision')),
  -- THREE INDEPENDENT AXES — never averaged, each with score+trend+rationale
  founder_axis_score     numeric,
  founder_axis_trend     text check (founder_axis_trend in ('improving','declining','stable')),
  founder_axis_rationale text,
  founder_axis_claim_ids uuid[],
  market_axis_score      numeric,
  market_axis_trend      text check (market_axis_trend in ('improving','declining','stable')),
  market_axis_verdict    text check (market_axis_verdict in ('bullish','neutral','bear')),
  market_axis_rationale  text,
  market_axis_swot       jsonb,
  market_axis_claim_ids  uuid[],
  idea_axis_score        numeric,
  idea_axis_trend        text check (idea_axis_trend in ('improving','declining','stable')),
  idea_axis_rationale    text,
  idea_axis_claim_ids    uuid[],
  -- decision
  decision_recommendation text check (decision_recommendation in ('Invest $100K','Decline','Request specific info')),
  decision_rationale      text,
  most_decisive_missing_datum text,
  memo             jsonb,
  reasoning_log_id uuid,
  -- speed instrumentation
  first_signal_at  timestamptz,
  decided_at       timestamptz,
  created_at       timestamptz not null default now()
);

-- ---------- REASONING_LOG: step-level chain-of-thought (Agentic Traceability) ----------
create table reasoning_log (
  log_id           uuid primary key default gen_random_uuid(),
  opportunity_id   uuid references opportunities(opportunity_id) on delete cascade,
  agent            text not null,            -- extraction | verification | screener | axis_scorer | memo | query
  step             integer,
  prompt           text,
  response         jsonb,
  model            text,
  created_at       timestamptz not null default now()
);

-- ---------- OUTREACH: outbound activation log ----------
create table outreach (
  outreach_id      uuid primary key default gen_random_uuid(),
  founder_id       uuid references founders(founder_id) on delete cascade,
  channel          text,
  message          text,
  converted_to_application boolean not null default false,
  created_at       timestamptz not null default now()
);

-- ---------- helpful indexes ----------
create index on signals (founder_id);
create index on claims (company_id);
create index on opportunities (stage);
create index on opportunities (founder_id);
create index on founder_score_history (founder_id, at);

-- speed metric view: median signal->decision time
create or replace view speed_metric as
select
  percentile_cont(0.5) within group (order by extract(epoch from (decided_at - first_signal_at))) as median_seconds,
  count(*) as decided_count
from opportunities
where decided_at is not null and first_signal_at is not null;
