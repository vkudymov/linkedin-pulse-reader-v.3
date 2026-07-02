import Link from "next/link";
import { redirect } from "next/navigation";

import { PostCard } from "@/components/PostCard";
import { PostFilters, type PostFilter } from "@/components/PostFilters";
import { log } from "@/lib/log/logger";
import { createSupabaseServerClient } from "@/lib/supabase/server";
import type { FeedPostRow, LinkedInAccountRow } from "@/types/database";

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

  const accountsResp = await supabase
    .from("linkedin_accounts")
    .select("id,label,li_profile_url,created_at")
    .order("created_at", { ascending: false });
  if (accountsResp.error) {
    log.error("posts", "failed to load linkedin_accounts", {
      where: "src/app/posts/page.tsx",
      meta: { code: accountsResp.error.code },
      hint: "Check RLS and Supabase settings.",
    });
  }

  const accounts = (accountsResp.data || []) as LinkedInAccountRow[];
  const accountIds = accounts.map((a) => a.id).filter(Boolean);

  let posts: FeedPostRow[] = [];
  if (accountIds.length > 0) {
    const postsResp = await supabase
      .from("feed_posts")
      .select("*")
      .in("linkedin_account_id", accountIds)
      .order("fetched_at", { ascending: false })
      .limit(100);
    if (postsResp.error) {
      log.error("posts", "failed to load feed_posts", {
        where: "src/app/posts/page.tsx",
        meta: { code: postsResp.error.code },
        hint: "Check RLS and Supabase settings.",
      });
    }

    posts = (postsResp.data || []) as FeedPostRow[];
  }

  if (filter === "relevant") posts = posts.filter((p) => p.is_relevant === true);
  if (filter === "rejected") posts = posts.filter((p) => p.is_relevant === false);

  return (
    <div className="min-h-[calc(100vh-1px)] bg-zinc-50">
      <header className="border-b border-zinc-200 bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-6 py-4">
          <div className="min-w-0">
            <div className="truncate text-base font-semibold text-zinc-900">
              Найденные посты
            </div>
            <div className="text-sm text-zinc-600">
              Аккаунтов LinkedIn: {accounts.length}
            </div>
          </div>
          <nav className="flex items-center gap-3">
            <Link className="text-sm underline" href="/logout">
              Выйти
            </Link>
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-5xl space-y-6 px-6 py-6">
        <PostFilters filter={filter} />

        {accounts.length === 0 ? (
          <div className="rounded-2xl border border-zinc-200 bg-white p-6">
            <div className="text-base font-semibold text-zinc-900">
              LinkedIn-аккаунт ещё не создан
            </div>
            <div className="mt-2 text-sm text-zinc-700">
              Запустите сбор постов через{" "}
              <code className="rounded bg-zinc-100 px-1 py-0.5">backend/run_demo.py</code>
              , чтобы создать запись в <code>linkedin_accounts</code> и загрузить{" "}
              <code>feed_posts</code>.
            </div>
          </div>
        ) : null}

        {accounts.length > 0 && posts.length === 0 ? (
          <div className="rounded-2xl border border-zinc-200 bg-white p-6">
            <div className="text-base font-semibold text-zinc-900">Постов пока нет</div>
            <div className="mt-2 text-sm text-zinc-700">
              Запустите <code className="rounded bg-zinc-100 px-1 py-0.5">backend/run_demo.py</code>{" "}
              и затем обновите страницу.
            </div>
          </div>
        ) : null}

        <div className="space-y-4">
          {posts.map((post) => (
            <PostCard key={post.id} post={post} />
          ))}
        </div>
      </main>
    </div>
  );
}

