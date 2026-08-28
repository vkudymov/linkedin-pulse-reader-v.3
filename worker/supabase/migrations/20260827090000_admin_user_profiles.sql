-- Admin functionality: add admin/blocking/counter fields to user_profiles.
-- Requirement: `is_admin` must be physically after `id`, so we rebuild the table.

begin;

-- 1) Create new table with required column order
create table if not exists public.user_profiles_new (
  id uuid primary key references auth.users (id) on delete cascade,
  is_admin boolean not null default false,

  full_name text,
  phone text,
  avatar_url text,
  company text,
  job_title text,
  date_of_birth date,
  city text,
  bio text,
  website text,

  search_prompt text,
  comment_prompt text,

  is_blocked boolean not null default false,
  blocked_at timestamptz,
  post_search_run_count integer not null default 0,

  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- 2) Copy data from old table if it exists
do $$
begin
  if exists (
    select 1
    from information_schema.tables
    where table_schema = 'public' and table_name = 'user_profiles'
  ) then
    insert into public.user_profiles_new (
      id,
      is_admin,
      full_name,
      phone,
      avatar_url,
      company,
      job_title,
      date_of_birth,
      city,
      bio,
      website,
      search_prompt,
      comment_prompt,
      is_blocked,
      blocked_at,
      post_search_run_count,
      created_at,
      updated_at
    )
    select
      id,
      false,
      full_name,
      phone,
      avatar_url,
      company,
      job_title,
      date_of_birth,
      city,
      bio,
      website,
      search_prompt,
      comment_prompt,
      false,
      null,
      0,
      created_at,
      updated_at
    from public.user_profiles
    on conflict (id) do nothing;
  end if;
end $$;

-- 3) Swap tables (drop old one after rename)
do $$
begin
  if exists (
    select 1
    from information_schema.tables
    where table_schema = 'public' and table_name = 'user_profiles'
  ) then
    alter table public.user_profiles rename to user_profiles_old;
  end if;
end $$;

alter table public.user_profiles_new rename to user_profiles;

drop table if exists public.user_profiles_old;

-- 4) RLS policies (same as before: user can only access their own row)
alter table public.user_profiles enable row level security;

drop policy if exists user_profiles_select_own on public.user_profiles;
create policy user_profiles_select_own
  on public.user_profiles
  for select
  using (id = auth.uid());

drop policy if exists user_profiles_insert_own on public.user_profiles;
create policy user_profiles_insert_own
  on public.user_profiles
  for insert
  with check (id = auth.uid());

drop policy if exists user_profiles_update_own on public.user_profiles;
create policy user_profiles_update_own
  on public.user_profiles
  for update
  using (id = auth.uid())
  with check (id = auth.uid());

drop policy if exists user_profiles_delete_own on public.user_profiles;
create policy user_profiles_delete_own
  on public.user_profiles
  for delete
  using (id = auth.uid());

-- 5) Guardrails: prevent clients from writing privileged columns
create or replace function public.user_profiles_prevent_privileged_writes()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  -- Allow service-role requests
  if auth.role() = 'service_role' then
    return new;
  end if;

  if tg_op = 'INSERT' then
    if coalesce(new.is_admin,false) <> false
       or coalesce(new.is_blocked,false) <> false
       or new.blocked_at is not null
       or coalesce(new.post_search_run_count,0) <> 0
    then
      raise exception 'forbidden';
    end if;
    new.is_admin := false;
    new.is_blocked := false;
    new.blocked_at := null;
    new.post_search_run_count := 0;
    return new;
  end if;

  if (new.is_admin is distinct from old.is_admin)
     or (new.is_blocked is distinct from old.is_blocked)
     or (new.blocked_at is distinct from old.blocked_at)
     or (new.post_search_run_count is distinct from old.post_search_run_count)
  then
    raise exception 'forbidden';
  end if;

  return new;
end;
$$;

drop trigger if exists trg_user_profiles_privileged_columns on public.user_profiles;
create trigger trg_user_profiles_privileged_columns
before insert or update on public.user_profiles
for each row execute function public.user_profiles_prevent_privileged_writes();

commit;

