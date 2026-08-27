-- Post media storage: bucket + metadata table + RLS policies.
-- We store copies of LinkedIn post images so they can be displayed reliably
-- and deleted when a post is deleted.

create extension if not exists "pgcrypto";

-- Storage bucket for post images.
insert into storage.buckets (id, name, public)
values ('post_media', 'post_media', true)
on conflict (id) do update set public = excluded.public;

-- Metadata table to map posts to stored media objects.
create table if not exists public.feed_post_media (
  id uuid primary key default gen_random_uuid(),
  feed_post_id uuid not null references public.feed_posts (id) on delete cascade,
  original_url text not null,
  object_path text not null,
  public_url text not null,
  position integer not null,
  created_at timestamptz not null default now(),
  constraint feed_post_media_post_position_unique unique (feed_post_id, position),
  constraint feed_post_media_post_object_unique unique (feed_post_id, object_path)
);

create index if not exists feed_post_media_post_position_idx
  on public.feed_post_media (feed_post_id, position);

alter table public.feed_post_media enable row level security;

-- feed_post_media: access is granted via the owning feed_posts -> linkedin_accounts row.
drop policy if exists feed_post_media_select_via_post on public.feed_post_media;
create policy feed_post_media_select_via_post
  on public.feed_post_media
  for select
  using (
    exists (
      select 1
      from public.feed_posts p
      join public.linkedin_accounts a on a.id = p.linkedin_account_id
      where p.id = feed_post_media.feed_post_id
        and a.user_id = auth.uid()
    )
  );

drop policy if exists feed_post_media_insert_via_post on public.feed_post_media;
create policy feed_post_media_insert_via_post
  on public.feed_post_media
  for insert
  with check (
    exists (
      select 1
      from public.feed_posts p
      join public.linkedin_accounts a on a.id = p.linkedin_account_id
      where p.id = feed_post_media.feed_post_id
        and a.user_id = auth.uid()
    )
  );

drop policy if exists feed_post_media_update_via_post on public.feed_post_media;
create policy feed_post_media_update_via_post
  on public.feed_post_media
  for update
  using (
    exists (
      select 1
      from public.feed_posts p
      join public.linkedin_accounts a on a.id = p.linkedin_account_id
      where p.id = feed_post_media.feed_post_id
        and a.user_id = auth.uid()
    )
  )
  with check (
    exists (
      select 1
      from public.feed_posts p
      join public.linkedin_accounts a on a.id = p.linkedin_account_id
      where p.id = feed_post_media.feed_post_id
        and a.user_id = auth.uid()
    )
  );

drop policy if exists feed_post_media_delete_via_post on public.feed_post_media;
create policy feed_post_media_delete_via_post
  on public.feed_post_media
  for delete
  using (
    exists (
      select 1
      from public.feed_posts p
      join public.linkedin_accounts a on a.id = p.linkedin_account_id
      where p.id = feed_post_media.feed_post_id
        and a.user_id = auth.uid()
    )
  );

-- Storage policies: users can read public objects, and can write/delete only within their own folder.
-- Path convention: post_media/{user_id}/{feed_post_id}/{position}.{ext}

drop policy if exists post_media_read_public on storage.objects;
create policy post_media_read_public
  on storage.objects
  for select
  using (bucket_id = 'post_media');

drop policy if exists post_media_insert_own_folder on storage.objects;
create policy post_media_insert_own_folder
  on storage.objects
  for insert
  with check (
    bucket_id = 'post_media'
    and (storage.foldername(name))[1] = auth.uid()::text
  );

drop policy if exists post_media_update_own_folder on storage.objects;
create policy post_media_update_own_folder
  on storage.objects
  for update
  using (
    bucket_id = 'post_media'
    and (storage.foldername(name))[1] = auth.uid()::text
  )
  with check (
    bucket_id = 'post_media'
    and (storage.foldername(name))[1] = auth.uid()::text
  );

drop policy if exists post_media_delete_own_folder on storage.objects;
create policy post_media_delete_own_folder
  on storage.objects
  for delete
  using (
    bucket_id = 'post_media'
    and (storage.foldername(name))[1] = auth.uid()::text
  );

