-- Post Searches storage:
-- - post_searches: user-defined searches (search_prompt + comment_prompt + optional account_label)
-- - post_analyses: per (post_search, feed_post) AI match result + comment draft

begin;

create table if not exists public.post_searches (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  title text not null,
  search_prompt text not null,
  comment_prompt text,
  account_label text,
  status text not null default 'active' check (status in ('active', 'paused')),
  last_run_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists post_searches_user_id_idx
  on public.post_searches (user_id);

create index if not exists post_searches_user_status_idx
  on public.post_searches (user_id, status);

create table if not exists public.post_analyses (
  id uuid primary key default gen_random_uuid(),
  post_search_id uuid not null references public.post_searches (id) on delete cascade,
  feed_post_id uuid not null references public.feed_posts (id) on delete cascade,
  match boolean not null,
  score integer not null check (score >= 0 and score <= 100),
  reason text not null,
  matched_requirements jsonb not null default '[]'::jsonb,
  missing_requirements jsonb not null default '[]'::jsonb,
  red_flags jsonb not null default '[]'::jsonb,
  comment_text text,
  comment_error text,
  raw_payload jsonb,
  error text,
  analyzed_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint post_analyses_search_post_unique unique (post_search_id, feed_post_id)
);

create index if not exists post_analyses_search_analyzed_idx
  on public.post_analyses (post_search_id, analyzed_at desc);

create index if not exists post_analyses_feed_post_idx
  on public.post_analyses (feed_post_id);

alter table public.post_searches enable row level security;
alter table public.post_analyses enable row level security;

-- post_searches: user can only access own rows.
drop policy if exists post_searches_select_own on public.post_searches;
create policy post_searches_select_own
  on public.post_searches
  for select
  using (user_id = auth.uid());

drop policy if exists post_searches_insert_own on public.post_searches;
create policy post_searches_insert_own
  on public.post_searches
  for insert
  with check (user_id = auth.uid());

drop policy if exists post_searches_update_own on public.post_searches;
create policy post_searches_update_own
  on public.post_searches
  for update
  using (user_id = auth.uid())
  with check (user_id = auth.uid());

drop policy if exists post_searches_delete_own on public.post_searches;
create policy post_searches_delete_own
  on public.post_searches
  for delete
  using (user_id = auth.uid());

-- post_analyses: user can only access rows through owning post_searches.
drop policy if exists post_analyses_select_via_search on public.post_analyses;
create policy post_analyses_select_via_search
  on public.post_analyses
  for select
  using (
    exists (
      select 1
      from public.post_searches s
      where s.id = post_analyses.post_search_id
        and s.user_id = auth.uid()
    )
  );

drop policy if exists post_analyses_insert_via_search on public.post_analyses;
create policy post_analyses_insert_via_search
  on public.post_analyses
  for insert
  with check (
    exists (
      select 1
      from public.post_searches s
      where s.id = post_analyses.post_search_id
        and s.user_id = auth.uid()
    )
  );

drop policy if exists post_analyses_update_via_search on public.post_analyses;
create policy post_analyses_update_via_search
  on public.post_analyses
  for update
  using (
    exists (
      select 1
      from public.post_searches s
      where s.id = post_analyses.post_search_id
        and s.user_id = auth.uid()
    )
  )
  with check (
    exists (
      select 1
      from public.post_searches s
      where s.id = post_analyses.post_search_id
        and s.user_id = auth.uid()
    )
  );

drop policy if exists post_analyses_delete_via_search on public.post_analyses;
create policy post_analyses_delete_via_search
  on public.post_analyses
  for delete
  using (
    exists (
      select 1
      from public.post_searches s
      where s.id = post_analyses.post_search_id
        and s.user_id = auth.uid()
    )
  );

-- Auto-migrate existing user_prompts into a single default post search per user.
-- Ensure search_prompt is non-empty and contains <<<POST_TEXT>>> marker.
insert into public.post_searches (user_id, title, search_prompt, comment_prompt, status, created_at, updated_at)
select
  pr.id as user_id,
  'Default' as title,
  case
    when pr.search_prompt is not null and btrim(pr.search_prompt) <> '' and position('<<<POST_TEXT>>>' in pr.search_prompt) > 0
      then pr.search_prompt
    when pr.search_prompt is not null and btrim(pr.search_prompt) <> ''
      then pr.search_prompt || E'\n\n<<<POST_TEXT>>>'
    else
      'Return ONLY valid JSON with keys match, score, reason, matched_requirements, missing_requirements, red_flags.' || E'\n\n' ||
      'Post text:' || E'\n<<<POST_TEXT>>>'
  end as search_prompt,
  nullif(btrim(pr.comment_prompt), '') as comment_prompt,
  'active' as status,
  now() as created_at,
  now() as updated_at
from public.user_prompts pr
where pr.id is not null;

commit;

