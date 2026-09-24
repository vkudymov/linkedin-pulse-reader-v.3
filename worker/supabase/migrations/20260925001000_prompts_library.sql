-- Convert search-scoped prompts into a user-owned prompt library.
-- Searches reference selected prompts via *_prompt_id columns.

begin;

-- 1) Extend prompts with ownership + title.
alter table public.prompts
  add column if not exists user_id uuid;

alter table public.prompts
  add column if not exists title text;

-- Backfill ownership from the owning search row (skip if already migrated).
do $$
begin
  if exists (
    select 1
    from information_schema.columns
    where table_schema = 'public'
      and table_name = 'prompts'
      and column_name = 'search_id'
  ) then
    update public.prompts p
    set user_id = s.user_id
    from public.searches s
    where p.user_id is null
      and p.search_id = s.id;
  end if;
end $$;

-- Generate a short title from the first line of the body.
update public.prompts
set title = left(nullif(btrim(split_part(body, E'\n', 1)), ''), 80)
where title is null;

update public.prompts
set title = initcap(role) || ' prompt'
where title is null or btrim(title) = '';

delete from public.prompts where user_id is null;

alter table public.prompts
  alter column user_id set not null;

alter table public.prompts
  drop constraint if exists prompts_user_id_fkey;
alter table public.prompts
  add constraint prompts_user_id_fkey
  foreign key (user_id) references auth.users (id) on delete cascade;

create index if not exists prompts_user_id_idx on public.prompts (user_id);
create index if not exists prompts_user_role_idx on public.prompts (user_id, role);

alter table public.prompts
  alter column title set not null;

-- 2) Add prompt pointers to searches.
alter table public.searches
  add column if not exists filter_prompt_id uuid;
alter table public.searches
  add column if not exists search_prompt_id uuid;
alter table public.searches
  add column if not exists comment_prompt_id uuid;

-- Backfill pointers from existing per-search prompts (skip if already migrated).
do $$
begin
  if exists (
    select 1
    from information_schema.columns
    where table_schema = 'public'
      and table_name = 'prompts'
      and column_name = 'search_id'
  ) then
    update public.searches s
    set filter_prompt_id = p.id
    from public.prompts p
    where s.filter_prompt_id is null
      and p.search_id = s.id
      and p.role = 'filter';

    update public.searches s
    set search_prompt_id = p.id
    from public.prompts p
    where s.search_prompt_id is null
      and p.search_id = s.id
      and p.role = 'search';

    update public.searches s
    set comment_prompt_id = p.id
    from public.prompts p
    where s.comment_prompt_id is null
      and p.search_id = s.id
      and p.role = 'comment';
  end if;
end $$;

-- 3) Add FK constraints from searches to prompts.
alter table public.searches
  drop constraint if exists searches_filter_prompt_id_fkey;
alter table public.searches
  add constraint searches_filter_prompt_id_fkey
  foreign key (filter_prompt_id) references public.prompts (id) on delete set null;

alter table public.searches
  drop constraint if exists searches_search_prompt_id_fkey;
alter table public.searches
  add constraint searches_search_prompt_id_fkey
  foreign key (search_prompt_id) references public.prompts (id) on delete set null;

alter table public.searches
  drop constraint if exists searches_comment_prompt_id_fkey;
alter table public.searches
  add constraint searches_comment_prompt_id_fkey
  foreign key (comment_prompt_id) references public.prompts (id) on delete set null;

create index if not exists searches_filter_prompt_id_idx on public.searches (filter_prompt_id);
create index if not exists searches_search_prompt_id_idx on public.searches (search_prompt_id);
create index if not exists searches_comment_prompt_id_idx on public.searches (comment_prompt_id);

-- 4) Replace prompts RLS policies with ownership-based policies.
drop policy if exists prompts_select_via_search on public.prompts;
drop policy if exists prompts_insert_via_search on public.prompts;
drop policy if exists prompts_update_via_search on public.prompts;
drop policy if exists prompts_delete_via_search on public.prompts;

drop policy if exists prompts_select_own on public.prompts;
create policy prompts_select_own
  on public.prompts
  for select
  using (user_id = auth.uid());

drop policy if exists prompts_insert_own on public.prompts;
create policy prompts_insert_own
  on public.prompts
  for insert
  with check (user_id = auth.uid());

drop policy if exists prompts_update_own on public.prompts;
create policy prompts_update_own
  on public.prompts
  for update
  using (user_id = auth.uid())
  with check (user_id = auth.uid());

drop policy if exists prompts_delete_own on public.prompts;
create policy prompts_delete_own
  on public.prompts
  for delete
  using (user_id = auth.uid());

-- 5) Drop search-scoped linkage (search_id) from prompts.
alter table public.prompts
  drop constraint if exists prompts_search_id_fkey;

alter table public.prompts
  drop constraint if exists prompts_search_role_unique;

drop index if exists public.prompts_search_id_idx;

alter table public.prompts
  drop column if exists search_id;

commit;

