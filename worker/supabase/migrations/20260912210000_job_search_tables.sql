-- Job Search MVP storage:
-- - job_searches: user-defined searches (search_query + filter_prompt)
-- - jobs: deduped job listings per user
-- - job_analyses: per (job_search, job) AI match result

begin;

create table if not exists public.job_searches (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  title text not null,
  search_query text not null,
  location text,
  filter_prompt text not null,
  status text not null default 'active' check (status in ('active', 'paused')),
  last_run_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists job_searches_user_id_idx
  on public.job_searches (user_id);

create index if not exists job_searches_user_status_idx
  on public.job_searches (user_id, status);

create table if not exists public.jobs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  linkedin_account_id uuid not null references public.linkedin_accounts (id) on delete cascade,
  source_key text not null,
  linkedin_job_id text,
  job_url text not null,
  title text not null,
  company text,
  location text,
  description text,
  raw_extra jsonb,
  fetched_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint jobs_user_source_unique unique (user_id, source_key)
);

create index if not exists jobs_user_fetched_idx
  on public.jobs (user_id, fetched_at desc);

create index if not exists jobs_account_fetched_idx
  on public.jobs (linkedin_account_id, fetched_at desc);

create table if not exists public.job_analyses (
  id uuid primary key default gen_random_uuid(),
  job_search_id uuid not null references public.job_searches (id) on delete cascade,
  job_id uuid not null references public.jobs (id) on delete cascade,
  match boolean not null,
  score integer not null,
  reason text not null,
  matched_requirements jsonb not null default '[]'::jsonb,
  missing_requirements jsonb not null default '[]'::jsonb,
  red_flags jsonb not null default '[]'::jsonb,
  raw_payload jsonb,
  error text,
  analyzed_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint job_analyses_search_job_unique unique (job_search_id, job_id)
);

create index if not exists job_analyses_search_analyzed_idx
  on public.job_analyses (job_search_id, analyzed_at desc);

create index if not exists job_analyses_job_analyzed_idx
  on public.job_analyses (job_id, analyzed_at desc);

alter table public.job_searches enable row level security;
alter table public.jobs enable row level security;
alter table public.job_analyses enable row level security;

-- job_searches: user can only access own rows.
drop policy if exists job_searches_select_own on public.job_searches;
create policy job_searches_select_own
  on public.job_searches
  for select
  using (user_id = auth.uid());

drop policy if exists job_searches_insert_own on public.job_searches;
create policy job_searches_insert_own
  on public.job_searches
  for insert
  with check (user_id = auth.uid());

drop policy if exists job_searches_update_own on public.job_searches;
create policy job_searches_update_own
  on public.job_searches
  for update
  using (user_id = auth.uid())
  with check (user_id = auth.uid());

drop policy if exists job_searches_delete_own on public.job_searches;
create policy job_searches_delete_own
  on public.job_searches
  for delete
  using (user_id = auth.uid());

-- jobs: user can only access own rows; inserts/updates must reference an owned linkedin_account.
drop policy if exists jobs_select_own on public.jobs;
create policy jobs_select_own
  on public.jobs
  for select
  using (user_id = auth.uid());

drop policy if exists jobs_insert_via_account on public.jobs;
create policy jobs_insert_via_account
  on public.jobs
  for insert
  with check (
    user_id = auth.uid()
    and exists (
      select 1
      from public.linkedin_accounts a
      where a.id = jobs.linkedin_account_id
        and a.user_id = auth.uid()
    )
  );

drop policy if exists jobs_update_via_account on public.jobs;
create policy jobs_update_via_account
  on public.jobs
  for update
  using (
    user_id = auth.uid()
    and exists (
      select 1
      from public.linkedin_accounts a
      where a.id = jobs.linkedin_account_id
        and a.user_id = auth.uid()
    )
  )
  with check (
    user_id = auth.uid()
    and exists (
      select 1
      from public.linkedin_accounts a
      where a.id = jobs.linkedin_account_id
        and a.user_id = auth.uid()
    )
  );

drop policy if exists jobs_delete_own on public.jobs;
create policy jobs_delete_own
  on public.jobs
  for delete
  using (user_id = auth.uid());

-- job_analyses: access is granted via owning job_search row (and matching job ownership).
drop policy if exists job_analyses_select_via_search on public.job_analyses;
create policy job_analyses_select_via_search
  on public.job_analyses
  for select
  using (
    exists (
      select 1
      from public.job_searches s
      where s.id = job_analyses.job_search_id
        and s.user_id = auth.uid()
    )
  );

drop policy if exists job_analyses_insert_via_search on public.job_analyses;
create policy job_analyses_insert_via_search
  on public.job_analyses
  for insert
  with check (
    exists (
      select 1
      from public.job_searches s
      where s.id = job_analyses.job_search_id
        and s.user_id = auth.uid()
    )
    and exists (
      select 1
      from public.jobs j
      where j.id = job_analyses.job_id
        and j.user_id = auth.uid()
    )
  );

drop policy if exists job_analyses_update_via_search on public.job_analyses;
create policy job_analyses_update_via_search
  on public.job_analyses
  for update
  using (
    exists (
      select 1
      from public.job_searches s
      where s.id = job_analyses.job_search_id
        and s.user_id = auth.uid()
    )
    and exists (
      select 1
      from public.jobs j
      where j.id = job_analyses.job_id
        and j.user_id = auth.uid()
    )
  )
  with check (
    exists (
      select 1
      from public.job_searches s
      where s.id = job_analyses.job_search_id
        and s.user_id = auth.uid()
    )
    and exists (
      select 1
      from public.jobs j
      where j.id = job_analyses.job_id
        and j.user_id = auth.uid()
    )
  );

drop policy if exists job_analyses_delete_via_search on public.job_analyses;
create policy job_analyses_delete_via_search
  on public.job_analyses
  for delete
  using (
    exists (
      select 1
      from public.job_searches s
      where s.id = job_analyses.job_search_id
        and s.user_id = auth.uid()
    )
  );

commit;

