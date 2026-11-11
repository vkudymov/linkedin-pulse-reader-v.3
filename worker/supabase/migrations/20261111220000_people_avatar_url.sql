-- LinkedIn profile photos for people-search results.

alter table public.people
  add column if not exists avatar_url text;
