-- Point each search run at one searches row.
-- Replaces search_runs.post_search_id and search_runs.job_search_id.

begin;

alter table public.search_runs
  add column if not exists search_id uuid;

update public.search_runs
set search_id = case
  when kind = 'job' then coalesce(job_search_id, post_search_id)
  else coalesce(post_search_id, job_search_id)
end
where search_id is null
  and (post_search_id is not null or job_search_id is not null);

alter table public.search_runs
  drop constraint if exists search_runs_post_search_id_fkey;
alter table public.search_runs
  drop constraint if exists search_runs_job_search_id_fkey;

drop index if exists public.search_runs_post_search_started_idx;
drop index if exists public.search_runs_job_search_started_idx;

alter table public.search_runs
  drop column if exists post_search_id;
alter table public.search_runs
  drop column if exists job_search_id;

alter table public.search_runs
  drop constraint if exists search_runs_search_id_fkey;
alter table public.search_runs
  add constraint search_runs_search_id_fkey
  foreign key (search_id) references public.searches (id) on delete set null;

create index if not exists search_runs_search_started_idx
  on public.search_runs (search_id, started_at desc);

commit;
