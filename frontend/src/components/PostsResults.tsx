"use client";

import { useMemo, useState, type ReactNode } from "react";
import { useTranslations } from "next-intl";

import {
  ListSearchSortBar,
  type ListSortDir,
  type ListSortField,
} from "@/components/ListSearchSortBar";
import { PostCard } from "@/components/PostCard";
import { PostFilters, type PostFilter, type PostFilterCounts } from "@/components/PostFilters";
import { parseJobPostedAtMs } from "@/lib/parseJobPostedAt";
import type { FeedPostMediaRow, FeedPostRow } from "@/types/database";

function timestampMs(value: string | null | undefined): number {
  if (!value) return 0;
  const ms = Date.parse(value);
  return Number.isNaN(ms) ? 0 : ms;
}

function payloadScore(payload: FeedPostRow["analysis_payload"]): number {
  const raw = payload?.score;
  if (typeof raw === "number" && Number.isFinite(raw)) return raw;
  if (typeof raw === "string" && raw.trim()) {
    const n = Number(raw);
    if (Number.isFinite(n)) return n;
  }
  return 0;
}

function postedMs(post: FeedPostRow): number {
  return parseJobPostedAtMs(post.published_at_text) ?? timestampMs(post.fetched_at);
}

function searchedMs(post: FeedPostRow): number {
  return timestampMs(post.analyzed_at) || timestampMs(post.fetched_at);
}

function sortValue(post: FeedPostRow, field: ListSortField): number {
  if (field === "score") return payloadScore(post.analysis_payload);
  if (field === "posted") return postedMs(post);
  return searchedMs(post);
}

function matchesQuery(post: FeedPostRow, query: string): boolean {
  if (!query) return true;
  const title = post.author_json?.name ?? "";
  const text = post.content ?? "";
  return `${title}\n${text}`.toLowerCase().includes(query);
}

export function PostsResults({
  header,
  posts,
  mediaByPostId,
  filter,
  counts,
  totalCount,
  accountsLength,
}: {
  header: ReactNode;
  posts: FeedPostRow[];
  mediaByPostId: Record<string, FeedPostMediaRow[]>;
  filter: PostFilter;
  counts?: PostFilterCounts;
  totalCount: number;
  accountsLength: number;
}) {
  const t = useTranslations("posts");
  const [query, setQuery] = useState("");
  const [sortField, setSortField] = useState<ListSortField>("searched");
  const [sortDir, setSortDir] = useState<ListSortDir>("desc");

  const normalizedQuery = query.trim().toLowerCase();

  const visible = useMemo(() => {
    const filtered = posts.filter((post) => matchesQuery(post, normalizedQuery));
    const dir = sortDir === "asc" ? 1 : -1;
    return [...filtered].sort((a, b) => {
      const delta = sortValue(a, sortField) - sortValue(b, sortField);
      if (delta !== 0) return delta * dir;
      return searchedMs(b) - searchedMs(a);
    });
  }, [posts, normalizedQuery, sortField, sortDir]);

  return (
    <>
      <div className="border-b border-border px-6 py-5">
        {header}
        <div className="mt-5 space-y-3">
          <PostFilters filter={filter} counts={counts} />
          {posts.length > 0 ? (
            <ListSearchSortBar
              query={query}
              onQueryChange={setQuery}
              sortField={sortField}
              onSortFieldChange={setSortField}
              sortDir={sortDir}
              onSortDirChange={setSortDir}
              labels={{
                placeholder: t("search.placeholder"),
                sortLabel: t("sort.label"),
                posted: t("sort.posted"),
                searched: t("sort.searched"),
                score: t("sort.score"),
                desc: t("sort.desc"),
                asc: t("sort.asc"),
              }}
            />
          ) : null}
        </div>
      </div>

      <div className="space-y-3 p-4">
        {accountsLength === 0 ? (
          <div className="rounded-2xl border border-border bg-secondary p-6">
            <h3 className="text-base font-semibold">{t("empty.noAccount.title")}</h3>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              {t("empty.noAccount.beforeScript")}{" "}
              <code className="rounded-md bg-background px-1.5 py-0.5 text-xs">
                worker/run_post_search.py
              </code>
              {t("empty.noAccount.afterScript")} <code>linkedin_accounts</code>{" "}
              {t("empty.noAccount.and")} <code>feed_posts</code>.
            </p>
          </div>
        ) : null}

        {accountsLength > 0 && posts.length === 0 ? (
          <div className="rounded-2xl border border-border bg-secondary p-6">
            <h3 className="text-base font-semibold">
              {filter === "all" ? t("empty.noPosts.titleAll") : t("empty.noPosts.titleFiltered")}
            </h3>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              {filter === "all" ? (
                <>
                  {t("empty.noPosts.runScript")}{" "}
                  <code className="rounded-md bg-background px-1.5 py-0.5 text-xs">
                    worker/run_post_search.py
                  </code>{" "}
                  {t("empty.noPosts.thenRefresh")}
                </>
              ) : (
                <>{t("empty.noPosts.tryAnotherFilter")}</>
              )}
            </p>
          </div>
        ) : null}

        {posts.length > 0 && visible.length === 0 ? (
          <div className="rounded-2xl border border-border bg-secondary p-6">
            <h3 className="text-base font-semibold">{t("search.empty")}</h3>
          </div>
        ) : null}

        {visible.length > 0 ? (
          <div className="space-y-4 pt-1">
            <p className="px-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">
              {t("shownCount", { shown: visible.length, total: totalCount })}
            </p>
            <div className="space-y-4">
              {visible.map((post) => (
                <PostCard key={post.id} post={post} media={mediaByPostId[post.id] || []} />
              ))}
            </div>
          </div>
        ) : null}
      </div>
    </>
  );
}
