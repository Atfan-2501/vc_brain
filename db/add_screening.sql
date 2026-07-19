-- Thesis Screener gate. Run once in the Supabase SQL editor.
alter table opportunities add column if not exists passed_screen boolean;
alter table opportunities add column if not exists thesis_fit text;       -- strong | partial | off_thesis
alter table opportunities add column if not exists screen_rationale text;
