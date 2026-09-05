import { redirect } from "next/navigation";
import { getTranslations } from "next-intl/server";

import { AppHeader } from "@/components/AppHeader";
import { PostCard } from "@/components/PostCard";
import { PostFilters, type PostFilter } from "@/components/PostFilters";
import { log } from "@/lib/log/logger";
import { requireNotBlocked } from "@/lib/auth/blocked";
import { createSupabaseServerClient } from "@/lib/supabase/server";
import type {
  FeedPostMediaRow,
  FeedPostRow,
  LinkedInAccountRow,
} from "@/types/database";

function normalizeFilter(raw: unknown): PostFilter {
  if (raw === "relevant" || raw === "rejected" || raw === "all") return raw;
  return "all";
}

export default async function PostsPage({
  params,
  searchParams,
}: {
  params: Promise<{ locale: string }>;
  searchParams: Promise<{ filter?: string }>;
}) {
  const { locale } = await params;
  const t = await getTranslations("posts");
  const { filter: rawFilter } = await searchParams;
  const filter = normalizeFilter(rawFilter);

  const supabase = await createSupabaseServerClient();
  const { data } = await supabase.auth.getUser();
  if (!data.user) redirect(`/${locale}/login`);
  const isAdmin = await requireNotBlocked(supabase, data.user.id);

  const accountsResp = await supabase
    .from("linkedin_accounts")
    .select("id,label,li_profile_url,created_at")
    .order("created_at", { ascending: false });
  if (accountsResp.error) {
    log.error("posts", "failed to load linkedin_accounts", {
      where: "src/app/[locale]/posts/page.tsx",
      meta: { code: accountsResp.error.code },
      hint: "Check RLS and Supabase settings.",
    });
  }

  const accounts = (accountsResp.data || []) as LinkedInAccountRow[];
  const accountIds = accounts.map((a) => a.id).filter(Boolean);

  let posts: FeedPostRow[] = [];
  let mediaByPostId: Record<string, FeedPostMediaRow[]> = {};
  if (accountIds.length > 0) {
    const postsResp = await supabase
      .from("feed_posts")
      .select("*")
      .in("linkedin_account_id", accountIds)
      .order("fetched_at", { ascending: false })
      .limit(100);
    if (postsResp.error) {
      log.error("posts", "failed to load feed_posts", {
        where: "src/app/[locale]/posts/page.tsx",
        meta: { code: postsResp.error.code },
        hint: "Check RLS and Supabase settings.",
      });
    }

    posts = (postsResp.data || []) as FeedPostRow[];

    const postIds = posts.map((p) => p.id).filter(Boolean);
    if (postIds.length > 0) {
      const mediaResp = await supabase
        .from("feed_post_media")
        .select("*")
        .in("feed_post_id", postIds)
        .order("position", { ascending: true });
      if (mediaResp.error) {
        log.error("posts", "failed to load feed_post_media", {
          where: "src/app/[locale]/posts/page.tsx",
          meta: { code: mediaResp.error.code },
        });
      } else {
        const rows = (mediaResp.data || []) as FeedPostMediaRow[];
        mediaByPostId = rows.reduce<Record<string, FeedPostMediaRow[]>>((acc, row) => {
          const key = row.feed_post_id;
          (acc[key] ||= []).push(row);
          return acc;
        }, {});
      }
    }
  }

  const counts = {
    all: posts.length,
    relevant: posts.filter((p) => p.is_relevant === true).length,
    rejected: posts.filter((p) => p.is_relevant === false).length,
    pending: posts.filter((p) => p.is_relevant == null).length,
  };

  if (filter === "relevant") posts = posts.filter((p) => p.is_relevant === true);
  if (filter === "rejected") posts = posts.filter((p) => p.is_relevant === false);

  return (
    <div className="min-h-screen bg-background text-foreground">
      <AppHeader
        title={t("titleFound")}
        subtitle={t("subtitleAccounts", { count: accounts.length })}
        active="posts"
        isAdmin={isAdmin}
      />

      <main className="mx-auto max-w-3xl px-6 py-6">
        <div className="overflow-hidden rounded-2xl border border-border bg-card">
          <div className="border-b border-border px-6 py-5">
            <div className="space-y-1">
              <h2 className="text-lg font-semibold tracking-tight">{t("feed.title")}</h2>
              <p className="max-w-xl text-sm leading-6 text-muted-foreground">
                {t("feed.description")}
              </p>
            </div>

            {counts.all > 0 ? (
              <div className="mt-4 flex flex-wrap gap-4 text-sm">
                <div>
                  <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                    {t("stats.total")}
                  </div>
                  <div className="mt-0.5 text-2xl font-semibold tabular-nums">
                    {counts.all}
                  </div>
                </div>
                <div>
                  <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                    {t("stats.accepted")}
                  </div>
                  <div className="mt-0.5 text-2xl font-semibold tabular-nums">
                    {counts.relevant}
                  </div>
                </div>
                <div>
                  <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                    {t("stats.rejected")}
                  </div>
                  <div className="mt-0.5 text-2xl font-semibold tabular-nums">
                    {counts.rejected}
                  </div>
                </div>
                {counts.pending > 0 ? (
                  <div>
                    <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                      {t("stats.pending")}
                    </div>
                    <div className="mt-0.5 text-2xl font-semibold tabular-nums">
                      {counts.pending}
                    </div>
                  </div>
                ) : null}
              </div>
            ) : null}

            <div className="mt-5">
              <PostFilters filter={filter} counts={counts.all > 0 ? counts : undefined} />
            </div>
          </div>

          <div className="space-y-3 p-4">
            {accounts.length === 0 ? (
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

            {accounts.length > 0 && posts.length === 0 ? (
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

            {posts.length > 0 ? (
              <div className="space-y-4 pt-1">
                <p className="px-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  {t("shownCount", { shown: posts.length, total: counts.all })}
                </p>
                <div className="space-y-4">
                  {posts.map((post) => (
                    <PostCard
                      key={post.id}
                      post={post}
                      media={mediaByPostId[post.id] || []}
                    />
                  ))}
                </div>
              </div>
            ) : null}
          </div>
        </div>
      </main>
    </div>
  );
}

