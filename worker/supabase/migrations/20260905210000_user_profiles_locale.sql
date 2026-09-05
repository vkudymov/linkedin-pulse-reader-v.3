-- UI locale for frontend i18n (separate from future LinkedIn contentLanguages).

alter table public.user_profiles
  add column if not exists locale text not null default 'ru';

alter table public.user_profiles
  drop constraint if exists user_profiles_locale_check;
alter table public.user_profiles
  add constraint user_profiles_locale_check check (locale in ('ru', 'en'));

comment on column public.user_profiles.locale is
  'UI language (short BCP-47). Separate from future LinkedIn contentLanguages.';

-- Keep user_profiles_view backward-compatible and include locale for UI.
create or replace view public.user_profiles_view as
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
  p.locale,
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

