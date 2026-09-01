-- Split public.user_profiles into 3 tables:
-- - public.user_profiles (human profile only)
-- - public.user_prompts (LLM prompts)
-- - public.user_admin_state (admin/block/counter)
-- Plus view: public.user_profiles_view for backward-compatible reads.

begin;

-- 0) Rename current user_profiles to legacy (keep data for copy)
do $$
begin
  if exists (
    select 1
    from information_schema.tables
    where table_schema = 'public' and table_name = 'user_profiles'
  ) and not exists (
    select 1
    from information_schema.tables
    where table_schema = 'public' and table_name = 'user_profiles_legacy'
  ) then
    alter table public.user_profiles rename to user_profiles_legacy;
  end if;
end $$;

-- 1) Human profile table
create table if not exists public.user_profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  full_name text,
  phone text,
  avatar_url text,
  company text,
  job_title text,
  date_of_birth date,
  city text,
  bio text,
  website text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- 2) Prompts table
create table if not exists public.user_prompts (
  id uuid primary key references auth.users (id) on delete cascade,
  search_prompt text,
  comment_prompt text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- 3) Admin state table
create table if not exists public.user_admin_state (
  id uuid primary key references auth.users (id) on delete cascade,
  is_admin boolean not null default false,
  is_blocked boolean not null default false,
  blocked_at timestamptz,
  post_search_run_count integer not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- 4) Copy data from legacy if present (best-effort: tolerates missing columns)
do $$
declare
  has_search_prompt boolean;
  has_comment_prompt boolean;
  has_is_admin boolean;
  has_is_blocked boolean;
  has_blocked_at boolean;
  has_post_search_run_count boolean;
  q text;
begin
  if exists (
    select 1
    from information_schema.tables
    where table_schema = 'public' and table_name = 'user_profiles_legacy'
  ) then
    select exists (
      select 1 from information_schema.columns
      where table_schema = 'public' and table_name = 'user_profiles_legacy' and column_name = 'search_prompt'
    ) into has_search_prompt;
    select exists (
      select 1 from information_schema.columns
      where table_schema = 'public' and table_name = 'user_profiles_legacy' and column_name = 'comment_prompt'
    ) into has_comment_prompt;
    select exists (
      select 1 from information_schema.columns
      where table_schema = 'public' and table_name = 'user_profiles_legacy' and column_name = 'is_admin'
    ) into has_is_admin;
    select exists (
      select 1 from information_schema.columns
      where table_schema = 'public' and table_name = 'user_profiles_legacy' and column_name = 'is_blocked'
    ) into has_is_blocked;
    select exists (
      select 1 from information_schema.columns
      where table_schema = 'public' and table_name = 'user_profiles_legacy' and column_name = 'blocked_at'
    ) into has_blocked_at;
    select exists (
      select 1 from information_schema.columns
      where table_schema = 'public' and table_name = 'user_profiles_legacy' and column_name = 'post_search_run_count'
    ) into has_post_search_run_count;

    -- human profile (assumes base columns exist)
    insert into public.user_profiles (
      id, full_name, phone, avatar_url, company, job_title, date_of_birth, city, bio, website, created_at, updated_at
    )
    select
      id, full_name, phone, avatar_url, company, job_title, date_of_birth, city, bio, website, created_at, updated_at
    from public.user_profiles_legacy
    on conflict (id) do update set
      full_name = excluded.full_name,
      phone = excluded.phone,
      avatar_url = excluded.avatar_url,
      company = excluded.company,
      job_title = excluded.job_title,
      date_of_birth = excluded.date_of_birth,
      city = excluded.city,
      bio = excluded.bio,
      website = excluded.website,
      updated_at = excluded.updated_at;

    -- prompts (dynamic: missing columns -> null)
    q := format(
      'insert into public.user_prompts (id, search_prompt, comment_prompt, created_at, updated_at)
       select id, %s, %s, created_at, updated_at
       from public.user_profiles_legacy
       on conflict (id) do update set
         search_prompt = excluded.search_prompt,
         comment_prompt = excluded.comment_prompt,
         updated_at = excluded.updated_at',
      case when has_search_prompt then 'search_prompt' else 'null' end,
      case when has_comment_prompt then 'comment_prompt' else 'null' end
    );
    execute q;

    -- admin state (dynamic: missing columns -> defaults)
    q := format(
      'insert into public.user_admin_state (id, is_admin, is_blocked, blocked_at, post_search_run_count, created_at, updated_at)
       select
         id,
         %s,
         %s,
         %s,
         %s,
         created_at,
         updated_at
       from public.user_profiles_legacy
       on conflict (id) do update set
         is_admin = excluded.is_admin,
         is_blocked = excluded.is_blocked,
         blocked_at = excluded.blocked_at,
         post_search_run_count = excluded.post_search_run_count,
         updated_at = excluded.updated_at',
      case when has_is_admin then 'coalesce(is_admin,false)' else 'false' end,
      case when has_is_blocked then 'coalesce(is_blocked,false)' else 'false' end,
      case when has_blocked_at then 'blocked_at' else 'null' end,
      case when has_post_search_run_count then 'coalesce(post_search_run_count,0)' else '0' end
    );
    execute q;
  end if;
end $$;

-- 5) Signup trigger: ensure rows in all 3 tables
create or replace function public.create_user_profile_for_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.user_profiles (id) values (new.id)
    on conflict (id) do nothing;
  insert into public.user_prompts (id) values (new.id)
    on conflict (id) do nothing;
  insert into public.user_admin_state (id) values (new.id)
    on conflict (id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created_profile on auth.users;
create trigger on_auth_user_created_profile
  after insert on auth.users
  for each row execute function public.create_user_profile_for_new_user();

-- 6) RLS policies
alter table public.user_profiles enable row level security;
drop policy if exists user_profiles_select_own on public.user_profiles;
create policy user_profiles_select_own on public.user_profiles for select using (id = auth.uid());
drop policy if exists user_profiles_insert_own on public.user_profiles;
create policy user_profiles_insert_own on public.user_profiles for insert with check (id = auth.uid());
drop policy if exists user_profiles_update_own on public.user_profiles;
create policy user_profiles_update_own on public.user_profiles for update using (id = auth.uid()) with check (id = auth.uid());
drop policy if exists user_profiles_delete_own on public.user_profiles;
create policy user_profiles_delete_own on public.user_profiles for delete using (id = auth.uid());

alter table public.user_prompts enable row level security;
drop policy if exists user_prompts_select_own on public.user_prompts;
create policy user_prompts_select_own on public.user_prompts for select using (id = auth.uid());
drop policy if exists user_prompts_insert_own on public.user_prompts;
create policy user_prompts_insert_own on public.user_prompts for insert with check (id = auth.uid());
drop policy if exists user_prompts_update_own on public.user_prompts;
create policy user_prompts_update_own on public.user_prompts for update using (id = auth.uid()) with check (id = auth.uid());

alter table public.user_admin_state enable row level security;
drop policy if exists user_admin_state_select_own on public.user_admin_state;
create policy user_admin_state_select_own on public.user_admin_state for select using (id = auth.uid());
-- Writes are allowed only via service-role (worker API). Regular users can only read their own row.

-- 7) View for combined reads (backward-compatible columns)
drop view if exists public.user_profiles_view;
create view public.user_profiles_view as
select
  p.id,
  a.is_admin,
  p.full_name,
  p.phone,
  p.avatar_url,
  p.company,
  p.job_title,
  p.date_of_birth,
  p.city,
  p.bio,
  p.website,
  pr.search_prompt,
  pr.comment_prompt,
  a.is_blocked,
  a.blocked_at,
  a.post_search_run_count,
  p.created_at,
  p.updated_at
from public.user_profiles p
left join public.user_prompts pr on pr.id = p.id
left join public.user_admin_state a on a.id = p.id;

-- 8) Cleanup legacy table
drop table if exists public.user_profiles_legacy;

commit;

