-- Minimal storage schema for current iteration:
-- - linkedin_accounts: per-app-user LinkedIn session (cookies)
-- - feed_posts: ingested posts + latest analysis state

create extension if not exists "pgcrypto";

create table if not exists public.linkedin_accounts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  label text,
  li_profile_url text,
  cookies_json jsonb not null,
  cookies_updated_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists linkedin_accounts_user_id_idx
  on public.linkedin_accounts (user_id);

create table if not exists public.feed_posts (
  id uuid primary key default gen_random_uuid(),
  linkedin_account_id uuid not null references public.linkedin_accounts (id) on delete cascade,
  source_key text not null,
  urn text,
  post_url text not null,
  author_json jsonb,
  content text,
  published_at_text text,
  reactions_count integer,
  comments_count integer,
  media_urls jsonb not null default '[]'::jsonb,
  raw_extra jsonb,
  is_relevant boolean,
  comment_text text,
  analysis_error text,
  analysis_payload jsonb,
  fetched_at timestamptz not null default now(),
  analyzed_at timestamptz,
  constraint feed_posts_account_source_unique unique (linkedin_account_id, source_key)
);

create index if not exists feed_posts_account_fetched_idx
  on public.feed_posts (linkedin_account_id, fetched_at desc);

alter table public.linkedin_accounts enable row level security;
alter table public.feed_posts enable row level security;

