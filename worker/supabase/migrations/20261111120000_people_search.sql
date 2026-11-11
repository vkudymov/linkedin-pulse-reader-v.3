-- People search: type, prompt role, run kind, results tables.

begin;

alter table public.search_types drop constraint if exists search_types_code_check;
alter table public.search_types
  add constraint search_types_code_check check (code in ('jobs', 'posts', 'people'));

insert into public.search_types (code, title)
values ('people', 'People')
on conflict (code) do nothing;

alter table public.prompts drop constraint if exists prompts_role_check;
alter table public.prompts
  add constraint prompts_role_check check (role in ('filter', 'search', 'comment', 'people'));

alter table public.search_runs drop constraint if exists search_runs_kind_check;
alter table public.search_runs
  add constraint search_runs_kind_check check (kind in ('post', 'job', 'people'));

alter table public.searches
  add column if not exists people_prompt_id uuid;

alter table public.searches
  drop constraint if exists searches_people_prompt_id_fkey;

alter table public.searches
  add constraint searches_people_prompt_id_fkey
  foreign key (people_prompt_id) references public.prompts (id) on delete set null;

create index if not exists searches_people_prompt_id_idx on public.searches (people_prompt_id);

create table if not exists public.people (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  linkedin_account_id uuid not null references public.linkedin_accounts (id) on delete cascade,
  source_key text not null,
  public_id text,
  profile_url text not null,
  full_name text,
  headline text,
  location text,
  connection_degree text,
  about text,
  skills jsonb not null default '[]'::jsonb,
  current_company text,
  experience jsonb not null default '[]'::jsonb,
  education jsonb not null default '[]'::jsonb,
  raw_extra jsonb,
  fetched_at timestamptz not null default now(),
  enriched_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint people_user_source_unique unique (user_id, source_key)
);

create index if not exists people_user_fetched_idx
  on public.people (user_id, fetched_at desc);

create table if not exists public.people_analyses (
  id uuid primary key default gen_random_uuid(),
  search_id uuid not null references public.searches (id) on delete cascade,
  person_id uuid not null references public.people (id) on delete cascade,
  match boolean not null,
  score integer not null,
  reason text not null,
  matched_requirements jsonb not null default '[]'::jsonb,
  missing_requirements jsonb not null default '[]'::jsonb,
  red_flags jsonb not null default '[]'::jsonb,
  stage text not null default 'card' check (stage in ('card', 'profile')),
  raw_payload jsonb,
  error text,
  analyzed_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint people_analyses_search_person_unique unique (search_id, person_id)
);

create index if not exists people_analyses_search_analyzed_idx
  on public.people_analyses (search_id, analyzed_at desc);

alter table public.people enable row level security;
alter table public.people_analyses enable row level security;

drop policy if exists people_select_own on public.people;
create policy people_select_own
  on public.people
  for select
  using (user_id = auth.uid());

drop policy if exists people_insert_via_account on public.people;
create policy people_insert_via_account
  on public.people
  for insert
  with check (
    user_id = auth.uid()
    and exists (
      select 1
      from public.linkedin_accounts a
      where a.id = people.linkedin_account_id
        and a.user_id = auth.uid()
    )
  );

drop policy if exists people_update_via_account on public.people;
create policy people_update_via_account
  on public.people
  for update
  using (
    user_id = auth.uid()
    and exists (
      select 1
      from public.linkedin_accounts a
      where a.id = people.linkedin_account_id
        and a.user_id = auth.uid()
    )
  )
  with check (
    user_id = auth.uid()
    and exists (
      select 1
      from public.linkedin_accounts a
      where a.id = people.linkedin_account_id
        and a.user_id = auth.uid()
    )
  );

drop policy if exists people_delete_own on public.people;
create policy people_delete_own
  on public.people
  for delete
  using (user_id = auth.uid());

drop policy if exists people_analyses_select_via_search on public.people_analyses;
create policy people_analyses_select_via_search
  on public.people_analyses
  for select
  using (
    exists (
      select 1
      from public.searches s
      join public.search_types st on st.id = s.search_type_id
      where s.id = people_analyses.search_id
        and s.user_id = auth.uid()
        and st.code = 'people'
    )
  );

drop policy if exists people_analyses_insert_via_search on public.people_analyses;
create policy people_analyses_insert_via_search
  on public.people_analyses
  for insert
  with check (
    exists (
      select 1
      from public.searches s
      join public.search_types st on st.id = s.search_type_id
      where s.id = people_analyses.search_id
        and s.user_id = auth.uid()
        and st.code = 'people'
    )
    and exists (
      select 1
      from public.people p
      where p.id = people_analyses.person_id
        and p.user_id = auth.uid()
    )
  );

drop policy if exists people_analyses_update_via_search on public.people_analyses;
create policy people_analyses_update_via_search
  on public.people_analyses
  for update
  using (
    exists (
      select 1
      from public.searches s
      join public.search_types st on st.id = s.search_type_id
      where s.id = people_analyses.search_id
        and s.user_id = auth.uid()
        and st.code = 'people'
    )
  )
  with check (
    exists (
      select 1
      from public.searches s
      join public.search_types st on st.id = s.search_type_id
      where s.id = people_analyses.search_id
        and s.user_id = auth.uid()
        and st.code = 'people'
    )
    and exists (
      select 1
      from public.people p
      where p.id = people_analyses.person_id
        and p.user_id = auth.uid()
    )
  );

drop policy if exists people_analyses_delete_via_search on public.people_analyses;
create policy people_analyses_delete_via_search
  on public.people_analyses
  for delete
  using (
    exists (
      select 1
      from public.searches s
      join public.search_types st on st.id = s.search_type_id
      where s.id = people_analyses.search_id
        and s.user_id = auth.uid()
        and st.code = 'people'
    )
  );

commit;
