-- Email reports after running searches:
-- - search_tariffs.email_reports_enabled: admin allows/disallows this feature for a tariff
-- - post_searches/job_searches: user toggles + chosen output format
--
-- NOTE: This migration intentionally keeps defaults as "disabled" to avoid changing behavior
-- for existing users/searches.

begin;

-- 1) Tariff-level capability toggle
alter table public.search_tariffs
  add column if not exists email_reports_enabled boolean not null default false;

-- 2) Per-search user settings (posts)
alter table public.post_searches
  add column if not exists email_report_enabled boolean not null default false;

alter table public.post_searches
  add column if not exists email_report_format text not null default 'none';

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'post_searches_email_report_format_check'
  ) then
    alter table public.post_searches
      add constraint post_searches_email_report_format_check
      check (email_report_format in ('none','xlsx','docx','txt','json','xml'));
  end if;
end $$;

-- 3) Per-search user settings (jobs)
alter table public.job_searches
  add column if not exists email_report_enabled boolean not null default false;

alter table public.job_searches
  add column if not exists email_report_format text not null default 'none';

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'job_searches_email_report_format_check'
  ) then
    alter table public.job_searches
      add constraint job_searches_email_report_format_check
      check (email_report_format in ('none','xlsx','docx','txt','json','xml'));
  end if;
end $$;

commit;

