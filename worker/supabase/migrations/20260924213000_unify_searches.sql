-- Unify job_searches + post_searches into a single searches table.
-- Prompts are moved into a separate prompts table and linked to searches.
--
-- Goals:
-- - Store all searches in public.searches with a type discriminator (search_types).
-- - Preserve existing UUIDs for search rows so downstream tables keep working.
-- - Retain existing API behavior by keeping child-table column names the same
--   (job_analyses.job_search_id, post_analyses.post_search_id, search_runs.*_search_id).
--
-- NOTE: This migration drops public.job_searches and public.post_searches tables.

begin;

-- 1) Lookup table for search types.
create table if not exists public.search_types (
  id uuid primary key default gen_random_uuid(),
  code text not null unique check (code in ('jobs', 'posts')),
  title text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

insert into public.search_types (code, title)
values
  ('jobs', 'Jobs'),
  ('posts', 'Posts')
on conflict (code) do update
  set title = excluded.title,
      updated_at = now();

alter table public.search_types enable row level security;
drop policy if exists search_types_select_authenticated on public.search_types;
create policy search_types_select_authenticated
  on public.search_types
  for select
  to authenticated
  using (true);

-- 2) Unified searches table.
create table if not exists public.searches (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  search_type_id uuid not null references public.search_types (id) on delete restrict,

  title text not null,
  status text not null default 'active' check (status in ('active', 'paused')),
  last_run_at timestamptz,

  -- Shared optional linkage.
  search_tariff_id uuid references public.search_tariffs (id) on delete set null,

  -- Email reports (shared).
  email_report_enabled boolean not null default false,
  email_report_format text not null default 'none'
    check (email_report_format in ('none', 'xlsx', 'docx', 'txt', 'json', 'xml')),

  -- Job-search fields.
  search_query text,
  location text,
  linkedin_filters jsonb not null default '{}'::jsonb,

  -- Post-search fields.
  account_label text,

  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists searches_user_id_idx on public.searches (user_id);
create index if not exists searches_user_status_idx on public.searches (user_id, status);
create index if not exists searches_type_idx on public.searches (search_type_id);
create index if not exists searches_tariff_idx on public.searches (search_tariff_id);

alter table public.searches enable row level security;
drop policy if exists searches_select_own on public.searches;
create policy searches_select_own
  on public.searches
  for select
  using (user_id = auth.uid());

drop policy if exists searches_insert_own on public.searches;
create policy searches_insert_own
  on public.searches
  for insert
  with check (user_id = auth.uid());

drop policy if exists searches_update_own on public.searches;
create policy searches_update_own
  on public.searches
  for update
  using (user_id = auth.uid())
  with check (user_id = auth.uid());

drop policy if exists searches_delete_own on public.searches;
create policy searches_delete_own
  on public.searches
  for delete
  using (user_id = auth.uid());

-- 3) Prompts table linked to searches.
create table if not exists public.prompts (
  id uuid primary key default gen_random_uuid(),
  search_id uuid not null references public.searches (id) on delete cascade,
  role text not null check (role in ('filter', 'search', 'comment')),
  body text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint prompts_search_role_unique unique (search_id, role)
);

create index if not exists prompts_search_id_idx on public.prompts (search_id);

alter table public.prompts enable row level security;
drop policy if exists prompts_select_via_search on public.prompts;
create policy prompts_select_via_search
  on public.prompts
  for select
  using (
    exists (
      select 1
      from public.searches s
      where s.id = prompts.search_id
        and s.user_id = auth.uid()
    )
  );

drop policy if exists prompts_insert_via_search on public.prompts;
create policy prompts_insert_via_search
  on public.prompts
  for insert
  with check (
    exists (
      select 1
      from public.searches s
      where s.id = prompts.search_id
        and s.user_id = auth.uid()
    )
  );

drop policy if exists prompts_update_via_search on public.prompts;
create policy prompts_update_via_search
  on public.prompts
  for update
  using (
    exists (
      select 1
      from public.searches s
      where s.id = prompts.search_id
        and s.user_id = auth.uid()
    )
  )
  with check (
    exists (
      select 1
      from public.searches s
      where s.id = prompts.search_id
        and s.user_id = auth.uid()
    )
  );

drop policy if exists prompts_delete_via_search on public.prompts;
create policy prompts_delete_via_search
  on public.prompts
  for delete
  using (
    exists (
      select 1
      from public.searches s
      where s.id = prompts.search_id
        and s.user_id = auth.uid()
    )
  );

-- 4) Copy existing data preserving IDs.
insert into public.searches (
  id,
  user_id,
  search_type_id,
  title,
  status,
  last_run_at,
  search_tariff_id,
  email_report_enabled,
  email_report_format,
  search_query,
  location,
  linkedin_filters,
  created_at,
  updated_at
)
select
  js.id,
  js.user_id,
  (select id from public.search_types st where st.code = 'jobs'),
  js.title,
  js.status,
  js.last_run_at,
  js.search_tariff_id,
  js.email_report_enabled,
  js.email_report_format,
  js.search_query,
  js.location,
  coalesce(js.linkedin_filters, '{}'::jsonb),
  js.created_at,
  js.updated_at
from public.job_searches js
on conflict (id) do nothing;

insert into public.searches (
  id,
  user_id,
  search_type_id,
  title,
  status,
  last_run_at,
  search_tariff_id,
  email_report_enabled,
  email_report_format,
  account_label,
  created_at,
  updated_at
)
select
  ps.id,
  ps.user_id,
  (select id from public.search_types st where st.code = 'posts'),
  ps.title,
  ps.status,
  ps.last_run_at,
  ps.search_tariff_id,
  ps.email_report_enabled,
  ps.email_report_format,
  ps.account_label,
  ps.created_at,
  ps.updated_at
from public.post_searches ps
on conflict (id) do nothing;

-- Prompts: job filter prompt.
insert into public.prompts (search_id, role, body, created_at, updated_at)
select
  js.id,
  'filter',
  js.filter_prompt,
  js.created_at,
  js.updated_at
from public.job_searches js
on conflict (search_id, role) do update
  set body = excluded.body,
      updated_at = now();

-- Prompts: post search prompt.
insert into public.prompts (search_id, role, body, created_at, updated_at)
select
  ps.id,
  'search',
  ps.search_prompt,
  ps.created_at,
  ps.updated_at
from public.post_searches ps
on conflict (search_id, role) do update
  set body = excluded.body,
      updated_at = now();

-- Prompts: post comment prompt (optional).
insert into public.prompts (search_id, role, body, created_at, updated_at)
select
  ps.id,
  'comment',
  ps.comment_prompt,
  ps.created_at,
  ps.updated_at
from public.post_searches ps
where ps.comment_prompt is not null and btrim(ps.comment_prompt) <> ''
on conflict (search_id, role) do update
  set body = excluded.body,
      updated_at = now();

-- 5) Repoint foreign keys to public.searches.

-- job_analyses.job_search_id
alter table public.job_analyses
  drop constraint if exists job_analyses_job_search_id_fkey;
alter table public.job_analyses
  add constraint job_analyses_job_search_id_fkey
  foreign key (job_search_id) references public.searches (id) on delete cascade;

-- post_analyses.post_search_id
alter table public.post_analyses
  drop constraint if exists post_analyses_post_search_id_fkey;
alter table public.post_analyses
  add constraint post_analyses_post_search_id_fkey
  foreign key (post_search_id) references public.searches (id) on delete cascade;

-- search_runs.*_search_id
alter table public.search_runs
  drop constraint if exists search_runs_post_search_id_fkey;
alter table public.search_runs
  add constraint search_runs_post_search_id_fkey
  foreign key (post_search_id) references public.searches (id) on delete set null;

alter table public.search_runs
  drop constraint if exists search_runs_job_search_id_fkey;
alter table public.search_runs
  add constraint search_runs_job_search_id_fkey
  foreign key (job_search_id) references public.searches (id) on delete set null;

-- 6) Update RLS policies on analyses to use public.searches + type check.

-- job_analyses: access is granted via owning searches row of type jobs (and matching job ownership).
drop policy if exists job_analyses_select_via_search on public.job_analyses;
create policy job_analyses_select_via_search
  on public.job_analyses
  for select
  using (
    exists (
      select 1
      from public.searches s
      join public.search_types st on st.id = s.search_type_id
      where s.id = job_analyses.job_search_id
        and s.user_id = auth.uid()
        and st.code = 'jobs'
    )
  );

drop policy if exists job_analyses_insert_via_search on public.job_analyses;
create policy job_analyses_insert_via_search
  on public.job_analyses
  for insert
  with check (
    exists (
      select 1
      from public.searches s
      join public.search_types st on st.id = s.search_type_id
      where s.id = job_analyses.job_search_id
        and s.user_id = auth.uid()
        and st.code = 'jobs'
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
      from public.searches s
      join public.search_types st on st.id = s.search_type_id
      where s.id = job_analyses.job_search_id
        and s.user_id = auth.uid()
        and st.code = 'jobs'
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
      from public.searches s
      join public.search_types st on st.id = s.search_type_id
      where s.id = job_analyses.job_search_id
        and s.user_id = auth.uid()
        and st.code = 'jobs'
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
      from public.searches s
      join public.search_types st on st.id = s.search_type_id
      where s.id = job_analyses.job_search_id
        and s.user_id = auth.uid()
        and st.code = 'jobs'
    )
  );

-- post_analyses: access is granted via owning searches row of type posts.
drop policy if exists post_analyses_select_via_search on public.post_analyses;
create policy post_analyses_select_via_search
  on public.post_analyses
  for select
  using (
    exists (
      select 1
      from public.searches s
      join public.search_types st on st.id = s.search_type_id
      where s.id = post_analyses.post_search_id
        and s.user_id = auth.uid()
        and st.code = 'posts'
    )
  );

drop policy if exists post_analyses_insert_via_search on public.post_analyses;
create policy post_analyses_insert_via_search
  on public.post_analyses
  for insert
  with check (
    exists (
      select 1
      from public.searches s
      join public.search_types st on st.id = s.search_type_id
      where s.id = post_analyses.post_search_id
        and s.user_id = auth.uid()
        and st.code = 'posts'
    )
  );

drop policy if exists post_analyses_update_via_search on public.post_analyses;
create policy post_analyses_update_via_search
  on public.post_analyses
  for update
  using (
    exists (
      select 1
      from public.searches s
      join public.search_types st on st.id = s.search_type_id
      where s.id = post_analyses.post_search_id
        and s.user_id = auth.uid()
        and st.code = 'posts'
    )
  )
  with check (
    exists (
      select 1
      from public.searches s
      join public.search_types st on st.id = s.search_type_id
      where s.id = post_analyses.post_search_id
        and s.user_id = auth.uid()
        and st.code = 'posts'
    )
  );

drop policy if exists post_analyses_delete_via_search on public.post_analyses;
create policy post_analyses_delete_via_search
  on public.post_analyses
  for delete
  using (
    exists (
      select 1
      from public.searches s
      join public.search_types st on st.id = s.search_type_id
      where s.id = post_analyses.post_search_id
        and s.user_id = auth.uid()
        and st.code = 'posts'
    )
  );

-- 7) Drop old tables (data migrated).
drop table if exists public.job_searches;
drop table if exists public.post_searches;

commit;

