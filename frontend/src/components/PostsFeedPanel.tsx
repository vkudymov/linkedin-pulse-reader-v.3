"use client";

import { PostCard } from "@/components/PostCard";
import { PostFilters, type PostFilter } from "@/components/PostFilters";
import type { FeedPostMediaRow, FeedPostRow, LinkedInAccountRow } from "@/types/database";

export function PostsFeedPanel({
  accounts,
  posts,
  mediaByPostId,
  counts,
  filter,
  filterMode = "nav",
  onFilterChange,
  deleteUrl,
  onPostDeleted,
  compact = false,
}: {
  accounts: LinkedInAccountRow[];
  posts: FeedPostRow[];
  mediaByPostId: Record<string, FeedPostMediaRow[]>;
  counts: { all: number; relevant: number; rejected: number; pending: number };
  filter: PostFilter;
  filterMode?: "nav" | "local";
  onFilterChange?: (next: PostFilter) => void;
  deleteUrl?: (postId: string) => string;
  onPostDeleted?: (postId: string) => void;
  compact?: boolean;
}) {
  const wrapperClassName = compact ? "overflow-hidden" : "overflow-hidden rounded-2xl border border-border bg-card";
  const headerClassName = compact ? "border-b border-border px-0 pb-5 pt-0" : "border-b border-border px-6 py-5";
  const bodyClassName = compact ? "space-y-3 px-0 pt-4" : "space-y-3 p-4";

  return (
    <div className={wrapperClassName}>
      <div className={headerClassName}>
        <div className="space-y-1">
          <h2 className="text-lg font-semibold tracking-tight">Лента постов</h2>
          <p className="max-w-xl text-sm leading-6 text-muted-foreground">
            Посты из LinkedIn с результатами AI-анализа — статус, причина отбора и черновик
            комментария видны сразу в списке.
          </p>
        </div>

        {counts.all > 0 ? (
          <div className="mt-4 flex flex-wrap gap-4 text-sm">
            <div>
              <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Всего
              </div>
              <div className="mt-0.5 text-2xl font-semibold tabular-nums">{counts.all}</div>
            </div>
            <div>
              <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Принято
              </div>
              <div className="mt-0.5 text-2xl font-semibold tabular-nums">{counts.relevant}</div>
            </div>
            <div>
              <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Отклонено
              </div>
              <div className="mt-0.5 text-2xl font-semibold tabular-nums">{counts.rejected}</div>
            </div>
            {counts.pending > 0 ? (
              <div>
                <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  Без проверки
                </div>
                <div className="mt-0.5 text-2xl font-semibold tabular-nums">{counts.pending}</div>
              </div>
            ) : null}
          </div>
        ) : null}

        <div className="mt-5">
          <PostFilters
            filter={filter}
            counts={counts.all > 0 ? counts : undefined}
            mode={filterMode}
            onFilterChange={onFilterChange}
          />
        </div>
      </div>

      <div className={bodyClassName}>
        {accounts.length === 0 ? (
          <div className="rounded-2xl border border-border bg-secondary p-6">
            <h3 className="text-base font-semibold">LinkedIn-аккаунт ещё не создан</h3>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              Запустите сбор постов через{" "}
              <code className="rounded-md bg-background px-1.5 py-0.5 text-xs">
                worker/run_post_search.py
              </code>
              , чтобы создать запись в <code>linkedin_accounts</code> и загрузить{" "}
              <code>feed_posts</code>.
            </p>
          </div>
        ) : null}

        {accounts.length > 0 && posts.length === 0 ? (
          <div className="rounded-2xl border border-border bg-secondary p-6">
            <h3 className="text-base font-semibold">
              {filter === "all" ? "Постов пока нет" : "Нет постов по этому фильтру"}
            </h3>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              {filter === "all" ? (
                <>
                  Запустите{" "}
                  <code className="rounded-md bg-background px-1.5 py-0.5 text-xs">
                    worker/run_post_search.py
                  </code>{" "}
                  и затем обновите страницу.
                </>
              ) : (
                <>Попробуйте другой фильтр или дождитесь новых результатов анализа.</>
              )}
            </p>
          </div>
        ) : null}

        {posts.length > 0 ? (
          <div className="space-y-4 pt-1">
            <p className="px-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Показано {posts.length} из {counts.all}
            </p>
            <div className="space-y-4">
              {posts.map((post) => (
                <PostCard
                  key={post.id}
                  post={post}
                  media={mediaByPostId[post.id] || []}
                  deleteUrl={deleteUrl ? deleteUrl(post.id) : undefined}
                  onDeleted={onPostDeleted ? () => onPostDeleted(post.id) : undefined}
                />
              ))}
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}

