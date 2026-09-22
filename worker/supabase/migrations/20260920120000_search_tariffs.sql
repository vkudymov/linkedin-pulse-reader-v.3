-- Search tariffs:
-- - search_tariffs: admin-defined quotas/thresholds for running searches
-- - user_admin_state.search_tariff_id: assigned by admin per user (optional)
-- - post_searches/job_searches.search_tariff_id: snapshot pointer per search (optional)

begin;

create table if not exists public.search_tariffs (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  max_scan_count integer not null check (max_scan_count >= 1 and max_scan_count <= 500),
  target_found_count integer not null check (target_found_count >= 1 and target_found_count <= 500),
  min_relevance_percent integer not null check (min_relevance_percent >= 0 and min_relevance_percent <= 100),
  sort_order integer not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists search_tariffs_sort_idx
  on public.search_tariffs (sort_order asc, created_at asc);

-- Seed a default tariff if table is empty.
insert into public.search_tariffs (title, max_scan_count, target_found_count, min_relevance_percent, sort_order)
select 'Стандартный', 25, 10, 70, 0
where not exists (select 1 from public.search_tariffs);

-- Add references (nullable; fallback to first tariff).
alter table public.user_admin_state
  add column if not exists search_tariff_id uuid references public.search_tariffs (id) on delete set null;

alter table public.post_searches
  add column if not exists search_tariff_id uuid references public.search_tariffs (id) on delete set null;

alter table public.job_searches
  add column if not exists search_tariff_id uuid references public.search_tariffs (id) on delete set null;

create index if not exists user_admin_state_search_tariff_idx
  on public.user_admin_state (search_tariff_id);

create index if not exists post_searches_tariff_idx
  on public.post_searches (search_tariff_id);

create index if not exists job_searches_tariff_idx
  on public.job_searches (search_tariff_id);

-- RLS: allow authenticated users to read tariffs (admin writes via service role / worker).
alter table public.search_tariffs enable row level security;

drop policy if exists search_tariffs_select_authenticated on public.search_tariffs;
create policy search_tariffs_select_authenticated
  on public.search_tariffs
  for select
  to authenticated
  using (true);

commit;

