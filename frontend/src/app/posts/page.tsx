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
      <header className="border-b border-border/80 bg-background">
        <div className="mx-auto flex max-w-3xl items-center justify-between gap-4 px-6 py-4">
          <div className="min-w-0">
            <h1 className="truncate text-base font-semibold tracking-tight">
              Найденные посты
            </h1>
            <p className="text-sm text-muted-foreground">
              Аккаунтов LinkedIn: {accounts.length}
            </p>
          </div>
          <nav className="flex items-center gap-3">
            <Link
              className="text-sm text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
              href="/logout"
            >
              Выйти
            </Link>
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-6 py-6">
        <div className="overflow-hidden rounded-2xl border border-border bg-card">
          <div className="border-b border-border px-6 py-5">
            <div className="space-y-1">
              <h2 className="text-lg font-semibold tracking-tight">Лента постов</h2>
              <p className="max-w-xl text-sm leading-6 text-muted-foreground">
                Посты из LinkedIn с результатами AI-анализа — статус, причина отбора и
                черновик комментария видны сразу в списке.
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
                  <div className="mt-0.5 text-2xl font-semibold tabular-nums">
                    {counts.relevant}
                  </div>
                </div>
                <div>
                  <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                    Отклонено
                  </div>
                  <div className="mt-0.5 text-2xl font-semibold tabular-nums">
                    {counts.rejected}
                  </div>
                </div>
                {counts.pending > 0 ? (
                  <div>
                    <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                      Без проверки
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
                <h3 className="text-base font-semibold">LinkedIn-аккаунт ещё не создан</h3>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">
                  Запустите сбор постов через{" "}
                  <code className="rounded-md bg-background px-1.5 py-0.5 text-xs">
                    backend/run_demo.py
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
                        backend/run_demo.py
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
                    <PostCard key={post.id} post={post} />
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
