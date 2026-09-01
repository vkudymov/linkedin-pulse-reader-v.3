-- User profile extension table (1:1 with auth.users).
-- Keep auth.users unchanged; store editable profile fields in public.user_profiles.

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

alter table public.user_profiles enable row level security;

-- RLS: user can only access their own row (id = auth.uid()).
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

-- Create an empty profile row at signup.
create or replace function public.create_user_profile_for_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.user_profiles (id)
  values (new.id)
  on conflict (id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created_profile on auth.users;
create trigger on_auth_user_created_profile
  after insert on auth.users
  for each row execute function public.create_user_profile_for_new_user();

