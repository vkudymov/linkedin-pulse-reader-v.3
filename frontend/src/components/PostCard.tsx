import { FeedPostRow } from "@/types/database";

function statusLabel(post: FeedPostRow): {
  label: string;
  className: string;
} {
  if (post.is_relevant === true) {
    return { label: "принято", className: "bg-emerald-50 text-emerald-800 border-emerald-200" };
  }
  if (post.is_relevant === false) {
    return { label: "отклонено", className: "bg-red-50 text-red-800 border-red-200" };
  }
  return { label: "не проверено", className: "bg-zinc-50 text-zinc-800 border-zinc-200" };
}

function getReason(post: FeedPostRow): string | null {
  if (post.analysis_error) return post.analysis_error;
  const payload = post.analysis_payload;
  const reason = payload?.reason;
  return typeof reason === "string" && reason.trim() ? reason.trim() : null;
}

export function PostCard({ post }: { post: FeedPostRow }) {
  const status = statusLabel(post);
  const authorName = post.author_json?.name || null;
  const authorHeadline = post.author_json?.headline || null;
  const authorProfileUrl =
    typeof post.author_json?.profile_url === "string" &&
    post.author_json.profile_url.trim()
      ? post.author_json.profile_url.trim()
      : null;
  const reason = getReason(post);

  return (
    <article className="rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="flex min-w-0 items-center gap-2">
            <div className="truncate text-sm font-medium text-zinc-900">
              {authorName || "Автор неизвестен"}
            </div>
            {authorProfileUrl ? (
              <a
                className="shrink-0 text-xs font-medium text-zinc-900 underline hover:text-zinc-700"
                href={authorProfileUrl}
                target="_blank"
                rel="noreferrer"
              >
                Профиль
              </a>
            ) : null}
          </div>
          {authorHeadline && (
            <div className="truncate text-xs text-zinc-600">{authorHeadline}</div>
          )}
        </div>

        <div
          className={[
            "inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-medium",
            status.className,
          ].join(" ")}
        >
          {status.label}
        </div>
      </div>

      {post.content && (
        <div className="mt-4 whitespace-pre-wrap text-sm leading-6 text-zinc-900">
          {post.content}
        </div>
      )}

      {reason && (
        <div className="mt-4 rounded-xl border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm text-zinc-800">
          <div className="text-xs font-medium text-zinc-600">Причина</div>
          <div className="mt-1 whitespace-pre-wrap">{reason}</div>
        </div>
      )}

      <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-zinc-600">
        {post.published_at_text && <div>Опубликовано: {post.published_at_text}</div>}
        {post.fetched_at && <div>Загружено: {new Date(post.fetched_at).toLocaleString()}</div>}
        {typeof post.reactions_count === "number" && (
          <div>Реакции: {post.reactions_count}</div>
        )}
        {typeof post.comments_count === "number" && (
          <div>Комментарии: {post.comments_count}</div>
        )}
      </div>

      {post.post_url ? (
        <div className="mt-4">
          <a
            className="text-sm font-medium text-zinc-900 underline"
            href={post.post_url}
            target="_blank"
            rel="noreferrer"
          >
            Открыть в LinkedIn
          </a>
        </div>
      ) : null}
    </article>
  );
}

