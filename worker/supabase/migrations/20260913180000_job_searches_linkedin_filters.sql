-- LinkedIn Jobs UI filters persisted per job search.

begin;

alter table public.job_searches
  add column if not exists linkedin_filters jsonb not null default '{}'::jsonb;

commit;
