import { redirect } from "next/navigation";
import { getTranslations } from "next-intl/server";

import { AppHeader } from "@/components/AppHeader";
import { PostsResults } from "@/components/PostsResults";
import { type PostFilter } from "@/components/PostFilters";
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
          <PostsResults
            header={<h2 className="text-lg font-semibold tracking-tight">{t("feed.title")}</h2>}
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

