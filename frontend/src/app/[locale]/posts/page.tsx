import { redirect } from "next/navigation";
import { getTranslations } from "next-intl/server";

import { AppHeader } from "@/components/AppHeader";
import { PostsResults } from "@/components/PostsResults";
import { type PostFilter } from "@/components/PostFilters";
import { Link } from "@/i18n/navigation";
import { log } from "@/lib/log/logger";
import { requireNotBlocked } from "@/lib/auth/blocked";
import { createSupabaseServerClient } from "@/lib/supabase/server";
import type {
  FeedPostMediaRow,
  FeedPostRow,
  LinkedInAccountRow,
} from "@/types/database";

type PostAnalysisRow = {
  feed_post_id: string;
  match: boolean;
  score: number;
  reason: string;
  matched_requirements: unknown;
  missing_requirements: unknown;
  red_flags: unknown;
  comment_text: string | null;
  comment_error: string | null;
  error: string | null;
  analyzed_at: string;
};

function normalizeFilter(raw: unknown): PostFilter {
  if (raw === "relevant" || raw === "rejected" || raw === "all") return raw;
  return "all";
}

export default async function PostsPage({
  params,
  searchParams,
}: {
  params: Promise<{ locale: string }>;
  searchParams: Promise<{ filter?: string; post_search_id?: string }>;
}) {
  const { locale } = await params;
  const t = await getTranslations("posts");
  const { filter: rawFilter, post_search_id: rawPostSearchId } = await searchParams;
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

  const postSearchesResp = await supabase
    .from("post_searches")
    .select("id,title,created_at")
    .eq("user_id", data.user.id)
    .order("created_at", { ascending: true });
  if (postSearchesResp.error) {
    log.error("posts", "failed to load post_searches", {
      where: "src/app/[locale]/posts/page.tsx",
      meta: { code: postSearchesResp.error.code },
    });
  }
  const postSearches = (postSearchesResp.data || []) as Array<{ id: string; title: string; created_at: string }>;
  const byId = new Set(postSearches.map((s) => s.id));
  const activePostSearchId =
    typeof rawPostSearchId === "string" && byId.has(rawPostSearchId)
      ? rawPostSearchId
      : postSearches[0]?.id ?? null;

  let posts: FeedPostRow[] = [];
  let mediaByPostId: Record<string, FeedPostMediaRow[]> = {};
  if (accountIds.length > 0 && activePostSearchId) {
    const analysesResp = await supabase
      .from("post_analyses")
      .select(
        "feed_post_id,match,score,reason,matched_requirements,missing_requirements,red_flags,comment_text,comment_error,error,analyzed_at",
      )
      .eq("post_search_id", activePostSearchId)
      .order("analyzed_at", { ascending: false })
      .limit(100);
    if (analysesResp.error) {
      log.error("posts", "failed to load post_analyses", {
        where: "src/app/[locale]/posts/page.tsx",
        meta: { code: analysesResp.error.code },
      });
    }
    const analyses = (analysesResp.data || []) as PostAnalysisRow[];
    const feedPostIds = analyses.map((a) => a.feed_post_id).filter(Boolean);
    if (feedPostIds.length > 0) {
      const postsResp = await supabase.from("feed_posts").select("*").in("id", feedPostIds);
      if (postsResp.error) {
        log.error("posts", "failed to load feed_posts by ids", {
          where: "src/app/[locale]/posts/page.tsx",
          meta: { code: postsResp.error.code },
        });
      }
      const rows = (postsResp.data || []) as FeedPostRow[];
      const postById = rows.reduce<Record<string, FeedPostRow>>((acc, row) => {
        acc[row.id] = row;
        return acc;
      }, {});

      posts = analyses
        .map((a) => {
          const post = postById[a.feed_post_id];
          if (!post) return null;
          return {
            ...post,
            is_relevant: typeof a.match === "boolean" ? a.match : null,
            comment_text: typeof a.comment_text === "string" ? a.comment_text : null,
            analysis_error:
              typeof a.error === "string"
                ? a.error
                : typeof a.comment_error === "string"
                  ? a.comment_error
                  : null,
            analysis_payload: {
              match: a.match,
              score: a.score,
              reason: a.reason,
              matched_requirements: a.matched_requirements,
              missing_requirements: a.missing_requirements,
              red_flags: a.red_flags,
            },
            analyzed_at: typeof a.analyzed_at === "string" ? a.analyzed_at : post.analyzed_at,
          };
        })
        .filter(Boolean) as FeedPostRow[];

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
          const mediaRows = (mediaResp.data || []) as FeedPostMediaRow[];
          mediaByPostId = mediaRows.reduce<Record<string, FeedPostMediaRow[]>>((acc, row) => {
            const key = row.feed_post_id;
            (acc[key] ||= []).push(row);
            return acc;
          }, {});
        }
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
        <div className="mb-6 flex gap-2">
          <Link
            href="/posts"
            className={[
              "rounded-full border px-4 py-2 text-sm",
              "border-border bg-card text-foreground",
            ].join(" ")}
          >
            {t("tabs.posts")}
          </Link>
          <Link
            href="/jobs"
            className={[
              "rounded-full border px-4 py-2 text-sm",
              "border-border/60 text-muted-foreground hover:text-foreground",
            ].join(" ")}
          >
            {t("tabs.jobs")}
          </Link>
        </div>

        <div className="overflow-hidden rounded-2xl border border-border bg-card">
          <PostsResults
            header={
              <div className="space-y-4">
                <h2 className="text-lg font-semibold tracking-tight">{t("feed.title")}</h2>
                {postSearches.length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    {postSearches.map((s) => {
                      const isActive = s.id === activePostSearchId;
                      const href =
                        filter === "all"
                          ? `/posts?post_search_id=${encodeURIComponent(s.id)}`
                          : `/posts?filter=${encodeURIComponent(filter)}&post_search_id=${encodeURIComponent(s.id)}`;
                      return (
                        <Link
                          key={s.id}
                          href={href}
                          className={[
                            "rounded-full border px-3 py-1.5 text-sm",
                            isActive
                              ? "border-border bg-background text-foreground"
                              : "border-border/60 text-muted-foreground hover:text-foreground",
                          ].join(" ")}
                        >
                          {s.title}
                        </Link>
                      );
                    })}
                  </div>
                ) : (
                  <div className="text-sm text-muted-foreground">{t("empty.noSearches")}</div>
                )}
              </div>
            }
            posts={posts}
            mediaByPostId={mediaByPostId}
            filter={filter}
            counts={counts.all > 0 ? counts : undefined}
            totalCount={counts.all}
            accountsLength={accounts.length}
          />
        </div>
      </main>
    </div>
  );
}

