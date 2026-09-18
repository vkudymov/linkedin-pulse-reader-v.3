"use client";

import { useEffect, useMemo, useState } from "react";

import { PostsFeedPanel } from "@/components/PostsFeedPanel";
import type { PostFilter } from "@/components/PostFilters";
import type { FeedPostMediaRow, FeedPostRow, LinkedInAccountRow } from "@/types/database";

type WorkerPostsResponse = {
  accounts: LinkedInAccountRow[];
  posts: FeedPostRow[];
  media_by_post_id: Record<string, FeedPostMediaRow[]>;
  counts: { all: number; relevant: number; rejected: number; pending: number };
};

export function AdminUserPostsSection({ userId }: { userId: string }) {
  const [filter, setFilter] = useState<PostFilter>("all");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<WorkerPostsResponse | null>(null);

  const mediaByPostId = useMemo(() => data?.media_by_post_id || {}, [data]);

  async function load(nextFilter: PostFilter) {
    setPending(true);
    setError(null);
    try {
      const resp = await fetch(
        `/api/admin/users/${encodeURIComponent(userId)}/posts?filter=${encodeURIComponent(nextFilter)}`,
        { method: "GET", cache: "no-store" },
      );
      if (!resp.ok) {
        const text = await resp.text().catch(() => "");
        throw new Error(text || "Не удалось загрузить посты.");
      }
      const json = (await resp.json()) as WorkerPostsResponse;
      setData(json);
    } catch (e: unknown) {
      setData(null);
      setError(e instanceof Error ? e.message : "Не удалось загрузить посты.");
    } finally {
      setPending(false);
    }
  }

  useEffect(() => {
    setFilter("all");
    void load("all");
    // eslint-disable-next-line react-hooks/exhaustive-deps -- reload on open/user change only
  }, [userId]);

  const accounts = data?.accounts || [];
  const posts = data?.posts || [];
  const counts = data?.counts || { all: 0, relevant: 0, rejected: 0, pending: 0 };

  function onFilterChange(next: PostFilter) {
    setFilter(next);
    void load(next);
  }

  function onPostDeleted(postId: string) {
    setData((prev) => {
      if (!prev) return prev;

      const post = prev.posts.find((p) => p.id === postId) || null;
      const nextPosts = prev.posts.filter((p) => p.id !== postId);
      const nextMediaByPostId = { ...prev.media_by_post_id };
      delete nextMediaByPostId[postId];

      const nextCounts = { ...prev.counts };
      nextCounts.all = Math.max(0, nextCounts.all - 1);
      if (post?.is_relevant === true) nextCounts.relevant = Math.max(0, nextCounts.relevant - 1);
      if (post?.is_relevant === false) nextCounts.rejected = Math.max(0, nextCounts.rejected - 1);
      if (post?.is_relevant == null) nextCounts.pending = Math.max(0, nextCounts.pending - 1);

      return {
        ...prev,
        posts: nextPosts,
        media_by_post_id: nextMediaByPostId,
        counts: nextCounts,
      };
    });
  }

  return (
    <div className="space-y-3">
      {error ? (
        <div className="rounded-xl border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {error}
        </div>
      ) : null}

      {pending && !data ? <div className="text-sm text-muted-foreground">Загружаем посты…</div> : null}

      {data ? (
        <PostsFeedPanel
          accounts={accounts}
          posts={posts}
          mediaByPostId={mediaByPostId}
          counts={counts}
          filter={filter}
          filterMode="local"
          onFilterChange={onFilterChange}
          deleteUrl={(postId) =>
            `/api/admin/users/${encodeURIComponent(userId)}/posts/${encodeURIComponent(postId)}`
          }
          onPostDeleted={onPostDeleted}
        />
      ) : null}
    </div>
  );
}

