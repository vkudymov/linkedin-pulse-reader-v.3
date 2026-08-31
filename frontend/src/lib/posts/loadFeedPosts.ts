import { log } from "@/lib/log/logger";
import type { FeedPostMediaRow, FeedPostRow, LinkedInAccountRow } from "@/types/database";

export type PostFilter = "all" | "relevant" | "rejected";

export type PostFilterCounts = {
  all: number;
  relevant: number;
  rejected: number;
  pending: number;
};

export function applyPostFilter(posts: FeedPostRow[], filter: PostFilter): FeedPostRow[] {
  if (filter === "relevant") return posts.filter((p) => p.is_relevant === true);
  if (filter === "rejected") return posts.filter((p) => p.is_relevant === false);
  return posts;
}

export function computePostCounts(posts: FeedPostRow[]): PostFilterCounts {
  return {
    all: posts.length,
    relevant: posts.filter((p) => p.is_relevant === true).length,
    rejected: posts.filter((p) => p.is_relevant === false).length,
    pending: posts.filter((p) => p.is_relevant == null).length,
  };
}

export async function loadLinkedInAccounts(
  supabase: any,
): Promise<LinkedInAccountRow[]> {
  const accountsResp = await supabase
    .from("linkedin_accounts")
    .select("id,label,li_profile_url,created_at")
    .order("created_at", { ascending: false });

  if (accountsResp.error) {
    log.error("posts", "failed to load linkedin_accounts", {
      where: "src/lib/posts/loadFeedPosts.ts",
      meta: { code: accountsResp.error.code },
      hint: "Check RLS and Supabase settings.",
    });
  }

  return (accountsResp.data || []) as LinkedInAccountRow[];
}

export async function loadFeedPostsForAccountIds(
  supabase: any,
  accountIds: string[],
  opts?: { limit?: number },
): Promise<{
  posts: FeedPostRow[];
  mediaByPostId: Record<string, FeedPostMediaRow[]>;
  counts: PostFilterCounts;
}> {
  const limit = opts?.limit ?? 100;

  if (!Array.isArray(accountIds) || accountIds.length === 0) {
    return { posts: [], mediaByPostId: {}, counts: computePostCounts([]) };
  }

  let posts: FeedPostRow[] = [];
  let mediaByPostId: Record<string, FeedPostMediaRow[]> = {};

  const postsResp = await supabase
    .from("feed_posts")
    .select("*")
    .in("linkedin_account_id", accountIds)
    .order("fetched_at", { ascending: false })
    .limit(limit);

  if (postsResp.error) {
    log.error("posts", "failed to load feed_posts", {
      where: "src/lib/posts/loadFeedPosts.ts",
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
        where: "src/lib/posts/loadFeedPosts.ts",
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

  const counts = computePostCounts(posts);
  return { posts, mediaByPostId, counts };
}

