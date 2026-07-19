-- ============================================================
-- VC Brain — synthetic seed data
-- 8 founders (incl. 2 cold-start), 8 companies, signals, claims
-- with 3 DELIBERATE contradictions for the demo's Verification Agent.
-- Run AFTER 02_schema.sql. Uses fixed UUIDs so you can reference them.
-- ============================================================

-- ---------- active thesis ----------
insert into theses (thesis_id, sectors, stages, geographies, check_size_usd, ownership_target_pct, risk_appetite, active) values
('11111111-0000-0000-0000-000000000001',
 array['AI infra','devtools','fintech'], array['pre-seed','seed'],
 array['EU','US'], 100000, 8, 'high', true);

-- ---------- founders ----------
-- Two have track records; two are cold-start (pre_track_record, wide interval, no github).
insert into founders (founder_id, name, github_handle, linkedin_slug, twitter_handle, domain, founder_score, founder_score_interval, is_pre_track_record) values
('f0000000-0000-0000-0000-000000000001','Jana Kessler','jkessler','jana-kessler','janakessler','kessler.ai', 78, 9,  false),
('f0000000-0000-0000-0000-000000000002','Marcus Vane','mvane-dev','marcus-vane',null,'vanelabs.io',        64, 12, false),
('f0000000-0000-0000-0000-000000000003','Priya Nandakumar',null,'priya-nandakumar',null,null,             49, 24, true),   -- cold-start
('f0000000-0000-0000-0000-000000000004','Tomas Reinhardt','treinhardt','tomas-reinhardt','tomasbuilds','reinhardt.dev', 71, 10, false),
('f0000000-0000-0000-0000-000000000005','Aisha Farouk',null,'aisha-farouk',null,null,                     41, 27, true),   -- cold-start
('f0000000-0000-0000-0000-000000000006','Leon Brandt','lbrandt','leon-brandt',null,'brandt.systems',      58, 14, false),
('f0000000-0000-0000-0000-000000000007','Sofia Ricci','sricci','sofia-ricci','sofiabuilds','ricci.tools',  69, 11, false),
('f0000000-0000-0000-0000-000000000008','David Okonkwo','dokonkwo','david-okonkwo',null,'okonkwo.ai',      66, 13, false);

-- founder score history (so trends render, not just snapshots)
insert into founder_score_history (founder_id, score, interval, at) values
('f0000000-0000-0000-0000-000000000001', 70, 14, now() - interval '90 days'),
('f0000000-0000-0000-0000-000000000001', 75, 11, now() - interval '30 days'),
('f0000000-0000-0000-0000-000000000001', 78, 9,  now() - interval '2 days'),
('f0000000-0000-0000-0000-000000000002', 60, 16, now() - interval '60 days'),
('f0000000-0000-0000-0000-000000000002', 64, 12, now() - interval '5 days'),
('f0000000-0000-0000-0000-000000000003', 45, 28, now() - interval '10 days'),
('f0000000-0000-0000-0000-000000000003', 49, 24, now() - interval '1 days');

-- ---------- companies ----------
insert into companies (company_id, name, founder_id, sector, geography, stage) values
('c0000000-0000-0000-0000-000000000001','Kessler AI',   'f0000000-0000-0000-0000-000000000001','AI infra','Berlin, EU','seed'),
('c0000000-0000-0000-0000-000000000002','VaneLabs',     'f0000000-0000-0000-0000-000000000002','devtools','Amsterdam, EU','pre-seed'),
('c0000000-0000-0000-0000-000000000003','NandaHealth',  'f0000000-0000-0000-0000-000000000003','fintech','London, EU','pre-seed'),
('c0000000-0000-0000-0000-000000000004','Reinhardt Data','f0000000-0000-0000-0000-000000000004','AI infra','Munich, EU','seed'),
('c0000000-0000-0000-0000-000000000005','Farouk Labs',  'f0000000-0000-0000-0000-000000000005','devtools','Cairo/Remote','pre-seed'),
('c0000000-0000-0000-0000-000000000006','Brandt Systems','f0000000-0000-0000-0000-000000000006','AI infra','Zurich, EU','seed'),
('c0000000-0000-0000-0000-000000000007','Ricci Tools',  'f0000000-0000-0000-0000-000000000007','devtools','Milan, EU','pre-seed'),
('c0000000-0000-0000-0000-000000000008','Okonkwo AI',   'f0000000-0000-0000-0000-000000000008','fintech','Lagos/Berlin','seed');

-- ---------- signals (mix of deck uploads + outbound detections) ----------
insert into signals (signal_id, founder_id, company_id, source, source_url, raw_content, tags, dedup_hash, ingested_at) values
('a0000000-0000-0000-0000-000000000001','f0000000-0000-0000-0000-000000000001','c0000000-0000-0000-0000-000000000001','deck','upload://kessler_deck.pdf','Series pre-seed deck, 12 slides','{inbound,deck}','sig-kessler-deck', now() - interval '2 days'),
('a0000000-0000-0000-0000-000000000002','f0000000-0000-0000-0000-000000000001','c0000000-0000-0000-0000-000000000001','github','https://github.com/jkessler/kessler-core','450 commits last 90d, 2.1k stars','{outbound,github}','sig-kessler-gh', now() - interval '3 days'),
('a0000000-0000-0000-0000-000000000003','f0000000-0000-0000-0000-000000000002','c0000000-0000-0000-0000-000000000002','show_hn','https://news.ycombinator.com/item?id=999001','Show HN: VaneLabs open-source CI cache','{outbound,show_hn}','sig-vane-hn', now() - interval '4 days'),
('a0000000-0000-0000-0000-000000000004','f0000000-0000-0000-0000-000000000003','c0000000-0000-0000-0000-000000000003','deck','upload://nanda_deck.pdf','Pre-seed deck, 9 slides','{inbound,deck}','sig-nanda-deck', now() - interval '1 days'),
('a0000000-0000-0000-0000-000000000005','f0000000-0000-0000-0000-000000000004','c0000000-0000-0000-0000-000000000004','producthunt','https://www.producthunt.com/posts/reinhardt-data','#2 Product of the Day','{outbound,producthunt}','sig-rein-ph', now() - interval '6 days'),
('a0000000-0000-0000-0000-000000000006','f0000000-0000-0000-0000-000000000005','c0000000-0000-0000-0000-000000000005','deck','upload://farouk_deck.pdf','Pre-seed deck, 10 slides','{inbound,deck}','sig-farouk-deck', now() - interval '1 days');

-- ============================================================
-- CLAIMS — including 3 SEEDED CONTRADICTIONS (marked below).
-- Leave trust_score / verification_status for the Verification
-- Agent to fill at demo time, OR pre-seed as shown for a canned demo.
-- ============================================================

-- Kessler AI — mostly clean, one strong verifiable claim
insert into claims (claim_id, company_id, source_signal_id, claim_text, claim_type, trust_score, verification_status, verification_evidence_url, source_ref) values
('d0000000-0000-0000-0000-000000000001','c0000000-0000-0000-0000-000000000001','a0000000-0000-0000-0000-000000000002','GitHub repo has 2.1k stars, 450 commits in 90 days','traction',0.94,'verified','https://github.com/jkessler/kessler-core','{"type":"web","url":"github.com/jkessler/kessler-core"}'),
('d0000000-0000-0000-0000-000000000002','c0000000-0000-0000-0000-000000000001','a0000000-0000-0000-0000-000000000001','Ex-DeepMind research engineer, 2 papers at NeurIPS','team',0.88,'verified','https://scholar.google.com/','{"type":"deck","slide_number":3}'),
('d0000000-0000-0000-0000-000000000003','c0000000-0000-0000-0000-000000000001','a0000000-0000-0000-0000-000000000001','ARR $120K from 4 enterprise pilots','traction',0.45,'unverified',null,'{"type":"deck","slide_number":8}'),
('d0000000-0000-0000-0000-000000000004','c0000000-0000-0000-0000-000000000001','a0000000-0000-0000-0000-000000000001','TAM $14B for AI inference tooling by 2028','market',0.7,'unverified',null,'{"type":"deck","slide_number":6}');

-- VaneLabs — CONTRADICTION #1: claims traction predating the launch
insert into claims (claim_id, company_id, source_signal_id, claim_text, claim_type, trust_score, verification_status, verification_evidence_url, contradiction_note, source_ref) values
('d0000000-0000-0000-0000-000000000005','c0000000-0000-0000-0000-000000000002','a0000000-0000-0000-0000-000000000003','$50K MRR with 300 paying teams','traction',0.2,'contradicted','https://news.ycombinator.com/item?id=999001','CONTRADICTION: Show HN launch was 3 weeks ago; $50K MRR + 300 paying teams implausible in that window','{"type":"deck","slide_number":7}'),
('d0000000-0000-0000-0000-000000000006','c0000000-0000-0000-0000-000000000002','a0000000-0000-0000-0000-000000000003','Product launched on Hacker News, 400 upvotes','traction',0.85,'verified','https://news.ycombinator.com/item?id=999001',null,'{"type":"web","url":"news.ycombinator.com/item?id=999001"}');

-- NandaHealth — cold-start founder, CONTRADICTION #2: fabricated credential
insert into claims (claim_id, company_id, source_signal_id, claim_text, claim_type, trust_score, verification_status, verification_evidence_url, contradiction_note, source_ref) values
('d0000000-0000-0000-0000-000000000007','c0000000-0000-0000-0000-000000000003','a0000000-0000-0000-0000-000000000004','Founder was Head of Risk at a top-3 EU neobank','team',0.25,'contradicted','https://www.linkedin.com/in/priya-nandakumar','CONTRADICTION: LinkedIn shows analyst (not Head of Risk) role; title inflated','{"type":"deck","slide_number":2}'),
('d0000000-0000-0000-0000-000000000008','c0000000-0000-0000-0000-000000000003','a0000000-0000-0000-0000-000000000004','Waitlist of 1,200 signups pre-launch','traction',0.5,'unverified',null,null,'{"type":"deck","slide_number":5}'),
('d0000000-0000-0000-0000-000000000009','c0000000-0000-0000-0000-000000000003','a0000000-0000-0000-0000-000000000004','Cap table','financial',null,'unverified',null,null,'{"type":"deck","slide_number":null}');  -- intentionally absent -> memo flags "Cap table: not disclosed"

-- Farouk Labs — cold-start, CONTRADICTION #3: market size vs cited source
insert into claims (claim_id, company_id, source_signal_id, claim_text, claim_type, trust_score, verification_status, verification_evidence_url, contradiction_note, source_ref) values
('d0000000-0000-0000-0000-000000000010','c0000000-0000-0000-0000-000000000005','a0000000-0000-0000-0000-000000000006','TAM $80B for developer productivity tools','market',0.3,'contradicted','https://www.gartner.com/','CONTRADICTION: cited analyst figure is ~$30B; $80B overstates by ~2.6x','{"type":"deck","slide_number":6}'),
('d0000000-0000-0000-0000-000000000011','c0000000-0000-0000-0000-000000000005','a0000000-0000-0000-0000-000000000006','Solo technical founder, strong writing, deep domain insight','team',0.55,'unverified',null,null,'{"type":"deck","slide_number":1}');

-- ---------- opportunities (both funnels converge) ----------
insert into opportunities (opportunity_id, company_id, founder_id, thesis_id, source, stage,
  founder_axis_score, founder_axis_trend, market_axis_score, market_axis_trend, market_axis_verdict,
  idea_axis_score, idea_axis_trend, first_signal_at) values
('e0000000-0000-0000-0000-000000000001','c0000000-0000-0000-0000-000000000001','f0000000-0000-0000-0000-000000000001','11111111-0000-0000-0000-000000000001','inbound','diligence', 9,'improving', 7,'stable','bullish', 8,'improving', now() - interval '3 days'),
('e0000000-0000-0000-0000-000000000002','c0000000-0000-0000-0000-000000000002','f0000000-0000-0000-0000-000000000002','11111111-0000-0000-0000-000000000001','outbound','screening', 6,'stable', 5,'stable','neutral', 4,'declining', now() - interval '4 days'),
('e0000000-0000-0000-0000-000000000003','c0000000-0000-0000-0000-000000000003','f0000000-0000-0000-0000-000000000003','11111111-0000-0000-0000-000000000001','inbound','screening', 4,'stable', 6,'improving','neutral', 5,'stable', now() - interval '1 days'),
('e0000000-0000-0000-0000-000000000005','c0000000-0000-0000-0000-000000000005','f0000000-0000-0000-0000-000000000005','11111111-0000-0000-0000-000000000001','inbound','sourcing', 5,'stable', 3,'declining','bear', 4,'stable', now() - interval '1 days');

-- NOTE for demo: leave one FRESH company (e.g. Ricci Tools / Okonkwo AI) WITHOUT
-- an opportunity row so you can run it live deck-in -> memo-out on stage.
