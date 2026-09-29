-- Atomic post-search quota increment, and a terminal status for runs
-- whose in-memory executor disappeared (worker restart).

begin;

create or replace function public.increment_post_search_run_count(p_user_id uuid)
returns integer
language plpgsql
security invoker
set search_path = public
as $$
declare
  new_count integer;
  blocked boolean;
begin
  update public.user_admin_state
  set post_search_run_count = post_search_run_count + 1,
      updated_at = now()
  where id = p_user_id
    and is_blocked = false
  returning post_search_run_count into new_count;

  if found then
    return new_count;
  end if;

  select is_blocked into blocked
  from public.user_admin_state
  where id = p_user_id;

  if not found then
    raise exception 'user_admin_state_missing';
  end if;

  if blocked then
    raise exception 'user_blocked';
  end if;

  raise exception 'post_search_run_count_not_incremented';
end;
$$;

revoke all on function public.increment_post_search_run_count(uuid) from public;
revoke all on function public.increment_post_search_run_count(uuid) from anon;
revoke all on function public.increment_post_search_run_count(uuid) from authenticated;
grant execute on function public.increment_post_search_run_count(uuid) to service_role;

alter table public.search_runs drop constraint if exists search_runs_status_check;
alter table public.search_runs
  add constraint search_runs_status_check
  check (status in ('running', 'done', 'error', 'lost'));

create index if not exists search_runs_session_id_idx
  on public.search_runs (session_id)
  where session_id is not null;

commit;
