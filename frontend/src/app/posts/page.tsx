import { redirect } from "next/navigation";

import { AppHeader } from "@/components/AppHeader";
import { PostsFeedPanel } from "@/components/PostsFeedPanel";
import { type PostFilter } from "@/components/PostFilters";
import { requireNotBlocked } from "@/lib/auth/blocked";
import {
  applyPostFilter,
  loadFeedPostsForAccountIds,
  loadLinkedInAccounts,
} from "@/lib/posts/loadFeedPosts";
import { createSupabaseServerClient } from "@/lib/supabase/server";
import type { FeedPostMediaRow, FeedPostRow, LinkedInAccountRow } from "@/types/database";

function normalizeFilter(raw: unknown): PostFilter {
  if (raw === "relevant" || raw === "rejected" || raw === "all") return raw;
  return "all";
}

export default async function PostsPage({
  searchParams,
}: {
  searchParams: Promise<{ filter?: string }>;
}) {
  const { filter: rawFilter } = await searchParams;
  const filter = normalizeFilter(rawFilter);

  const supabase = await createSupabaseServerClient();
  const { data } = await supabase.auth.getUser();
  if (!data.user) redirect("/login");
  const isAdmin = await requireNotBlocked(supabase, data.user.id);

  const accounts = (await loadLinkedInAccounts(supabase)) as LinkedInAccountRow[];
  const accountIds = accounts.map((a) => a.id).filter(Boolean);

  const { posts: allPosts, mediaByPostId, counts } = await loadFeedPostsForAccountIds(
    supabase,
    accountIds,
    { limit: 100 },
  );
  const posts = applyPostFilter(allPosts as FeedPostRow[], filter);

  return (
    <div className="min-h-screen bg-background text-foreground">
      <AppHeader
        title="Найденные посты"
        subtitle={`Аккаунтов LinkedIn: ${accounts.length}`}
        active="posts"
        isAdmin={isAdmin}
      />

      <main className="mx-auto max-w-3xl px-6 py-6">
        <PostsFeedPanel
          accounts={accounts}
          posts={posts}
          mediaByPostId={mediaByPostId}
          counts={counts}
          filter={filter}
        />
      </main>
    </div>
  );
}
