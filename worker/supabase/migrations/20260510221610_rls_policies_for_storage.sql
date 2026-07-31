-- RLS policies assume requests authenticated with a user JWT.
-- Service role bypasses RLS and can still be used for worker ingestion.

-- linkedin_accounts: a user can only see and mutate their own accounts.
drop policy if exists linkedin_accounts_select_own on public.linkedin_accounts;
create policy linkedin_accounts_select_own
  on public.linkedin_accounts
  for select
  using (user_id = auth.uid());

drop policy if exists linkedin_accounts_insert_own on public.linkedin_accounts;
create policy linkedin_accounts_insert_own
  on public.linkedin_accounts
  for insert
  with check (user_id = auth.uid());

drop policy if exists linkedin_accounts_update_own on public.linkedin_accounts;
create policy linkedin_accounts_update_own
  on public.linkedin_accounts
  for update
  using (user_id = auth.uid())
  with check (user_id = auth.uid());

drop policy if exists linkedin_accounts_delete_own on public.linkedin_accounts;
create policy linkedin_accounts_delete_own
  on public.linkedin_accounts
  for delete
  using (user_id = auth.uid());

-- feed_posts: access is granted via the owning linkedin_account row.
drop policy if exists feed_posts_select_via_account on public.feed_posts;
create policy feed_posts_select_via_account
  on public.feed_posts
  for select
  using (
    exists (
      select 1
      from public.linkedin_accounts a
      where a.id = feed_posts.linkedin_account_id
        and a.user_id = auth.uid()
    )
  );

drop policy if exists feed_posts_insert_via_account on public.feed_posts;
create policy feed_posts_insert_via_account
  on public.feed_posts
  for insert
  with check (
    exists (
      select 1
      from public.linkedin_accounts a
      where a.id = feed_posts.linkedin_account_id
        and a.user_id = auth.uid()
    )
  );

drop policy if exists feed_posts_update_via_account on public.feed_posts;
create policy feed_posts_update_via_account
  on public.feed_posts
  for update
  using (
    exists (
      select 1
      from public.linkedin_accounts a
      where a.id = feed_posts.linkedin_account_id
        and a.user_id = auth.uid()
    )
  )
  with check (
    exists (
      select 1
      from public.linkedin_accounts a
      where a.id = feed_posts.linkedin_account_id
        and a.user_id = auth.uid()
    )
  );

drop policy if exists feed_posts_delete_via_account on public.feed_posts;
create policy feed_posts_delete_via_account
  on public.feed_posts
  for delete
  using (
    exists (
      select 1
      from public.linkedin_accounts a
      where a.id = feed_posts.linkedin_account_id
        and a.user_id = auth.uid()
    )
  );

