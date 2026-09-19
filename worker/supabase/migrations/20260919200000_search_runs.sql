-- Admin audit log: each Post/Job search run (criteria + prompt snapshot + metrics).

begin;

create table if not exists public.search_runs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  kind text not null check (kind in ('post', 'job')),
  post_search_id uuid references public.post_searches (id) on delete set null,
  job_search_id uuid references public.job_searches (id) on delete set null,

  search_title text not null,
  limit_count integer not null,
  account_label text,

  search_query text,
  location text,
  linkedin_filters jsonb,

  search_prompt text,
  comment_prompt text,
  filter_prompt text,

  status text not null default 'running' check (status in ('running', 'done', 'error')),
  started_at timestamptz not null default now(),
  finished_at timestamptz,

  fetched_count integer,
  analyzed_count integer,
  matched_count integer,
  error text,

  session_id uuid,
  initiated_by text not null default 'user' check (initiated_by in ('user', 'admin')),
  admin_actor_id uuid references auth.users (id) on delete set null,

  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists search_runs_started_at_idx on public.search_runs (started_at desc);
create index if not exists search_runs_user_started_idx on public.search_runs (user_id, started_at desc);
create index if not exists search_runs_kind_started_idx on public.search_runs (kind, started_at desc);
create index if not exists search_runs_post_search_started_idx on public.search_runs (post_search_id, started_at desc);
create index if not exists search_runs_job_search_started_idx on public.search_runs (job_search_id, started_at desc);
create index if not exists search_runs_status_started_idx on public.search_runs (status, started_at desc);

alter table public.search_runs enable row level security;

commit;
