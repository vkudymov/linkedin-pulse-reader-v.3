-- Full Chrome-shaped session snapshot (cookies + storage + browser).
-- Keep cookies_json as the legacy Playwright (or exported cookie) list.

alter table public.linkedin_accounts
  add column if not exists session_snapshot jsonb;

comment on column public.linkedin_accounts.session_snapshot is
  'Chrome-shaped LinkedIn session snapshot (session_snapshot module). Null for legacy rows.';
