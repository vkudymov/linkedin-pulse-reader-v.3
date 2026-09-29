"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { ChevronDown, ChevronUp, RefreshCw } from "lucide-react";
import { useTranslations } from "next-intl";

import { useRouter } from "@/i18n/navigation";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import type { AdminUserOption } from "@/lib/admin/users";
import { cn } from "@/lib/utils";

type SearchOption = { id: string; title: string };

type SearchRunRow = {
  id: string;
  user_id: string;
  kind: "post" | "job" | string;
  search_id: string | null;
  search_title: string;
  limit_count: number;
  account_label: string | null;
  search_query: string | null;
  location: string | null;
  search_prompt: string | null;
  comment_prompt: string | null;
  filter_prompt: string | null;
  status: string;
  started_at: string;
  finished_at: string | null;
  fetched_count: number | null;
  analyzed_count: number | null;
  matched_count: number | null;
  error: string | null;
  initiated_by: string;
  user_full_name: string | null;
};

type ListResponse = {
  items: SearchRunRow[];
  total: number;
  limit: number;
  offset: number;
};

function formatDt(value: string | null, locale: "ru" | "en") {
  if (!value) return "—";
  const l = locale === "en" ? "en-US" : "ru-RU";
  return new Date(value).toLocaleString(l, {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function AdminSearchRunsPanel({
  locale,
  initialUsers = [],
}: {
  locale: "ru" | "en";
  initialUsers?: AdminUserOption[];
}) {
  const t = useTranslations("adminSearchRuns");
  const router = useRouter();
  const searchParams = useSearchParams();

  const userId = searchParams.get("user_id") || "";
  const kind = searchParams.get("kind") || "all";
  const searchId = searchParams.get("search_id") || "";
  const status = searchParams.get("status") || "all";
  const order = searchParams.get("order") || "desc";

  const [users] = useState<AdminUserOption[]>(initialUsers);
  const [searchOptionsByKey, setSearchOptionsByKey] = useState<Record<string, SearchOption[]>>({});
  const [rows, setRows] = useState<SearchRunRow[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [openPromptId, setOpenPromptId] = useState<string | null>(null);

  const selectedSearchId = kind === "post" || kind === "job" ? searchId : "";

  const searchOptionsKey =
    userId && (kind === "post" || kind === "job") ? `${userId}:${kind}` : null;
  const searchOptions = searchOptionsKey ? (searchOptionsByKey[searchOptionsKey] ?? []) : [];

  const queryString = useMemo(() => {
    const p = new URLSearchParams();
    if (userId) p.set("user_id", userId);
    if (kind === "post" || kind === "job") p.set("kind", kind);
    if ((kind === "post" || kind === "job") && searchId) p.set("search_id", searchId);
    if (status !== "all") p.set("status", status);
    if (order === "asc") p.set("order", "asc");
    p.set("limit", "50");
    p.set("offset", "0");
    return p.toString();
  }, [userId, kind, searchId, status, order]);

  const pushFilters = useCallback(
    (patch: Record<string, string>) => {
      const p = new URLSearchParams(searchParams.toString());
      for (const [k, v] of Object.entries(patch)) {
        if (!v || v === "all") p.delete(k);
        else p.set(k, v);
      }
      if (patch.kind !== undefined || patch.user_id !== undefined) {
        p.delete("search_id");
        p.delete("post_search_id");
        p.delete("job_search_id");
      }
      const query = Object.fromEntries(p.entries());
      router.replace({ pathname: "/admin/search-runs", query });
    },
    [router, searchParams],
  );

  useEffect(() => {
    if (!searchOptionsKey) return;
    const [uid, k] = searchOptionsKey.split(":");
    const path =
      k === "post"
        ? `/api/admin/users/${encodeURIComponent(uid)}/post-searches`
        : `/api/admin/users/${encodeURIComponent(uid)}/job-searches`;
    let cancelled = false;
    void (async () => {
      try {
        const resp = await fetch(path, { cache: "no-store" });
        const json = (await resp.json().catch(() => null)) as Array<{ id: string; title: string }> | null;
        if (cancelled) return;
        const next =
          resp.ok && Array.isArray(json) ? json.map((r) => ({ id: r.id, title: r.title })) : [];
        setSearchOptionsByKey((prev) => ({ ...prev, [searchOptionsKey]: next }));
      } catch {
        if (!cancelled) {
          setSearchOptionsByKey((prev) => ({ ...prev, [searchOptionsKey]: [] }));
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [searchOptionsKey]);

  const loadRuns = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await fetch(`/api/admin/search-runs?${queryString}`, { cache: "no-store" });
      const json = (await resp.json().catch(() => null)) as ListResponse | { detail?: string } | null;
      if (!resp.ok || !json || !("items" in json)) {
        throw new Error((json && "detail" in json && json.detail) || t("errors.load"));
      }
      setRows(json.items);
      setTotal(json.total);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t("errors.load"));
      setRows([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [queryString, t]);

  useEffect(() => {
    const handle = window.setTimeout(() => {
      void loadRuns();
    }, 0);
    return () => window.clearTimeout(handle);
  }, [loadRuns]);

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-border bg-card p-6">
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="grid gap-2">
            <Label>{t("filters.user")}</Label>
            <select
              className="h-11 rounded-full border border-border bg-secondary px-4 text-sm"
              value={userId}
              onChange={(e) => pushFilters({ user_id: e.target.value })}
            >
              <option value="">{t("filters.allUsers")}</option>
              {users.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.full_name || u.email || u.id}
                </option>
              ))}
            </select>
          </div>
          <div className="grid gap-2">
            <Label>{t("filters.kind")}</Label>
            <select
              className="h-11 rounded-full border border-border bg-secondary px-4 text-sm"
              value={kind}
              onChange={(e) => pushFilters({ kind: e.target.value })}
            >
              <option value="all">{t("filters.allKinds")}</option>
              <option value="post">{t("filters.posts")}</option>
              <option value="job">{t("filters.jobs")}</option>
            </select>
          </div>
          <div className="grid gap-2">
            <Label>{t("filters.search")}</Label>
            <select
              className="h-11 rounded-full border border-border bg-secondary px-4 text-sm disabled:opacity-50"
              value={selectedSearchId}
              disabled={!userId || kind === "all"}
              onChange={(e) => {
                const id = e.target.value;
                if (kind === "post" || kind === "job") pushFilters({ search_id: id });
              }}
            >
              <option value="">{t("filters.allSearches")}</option>
              {searchOptions.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.title}
                </option>
              ))}
            </select>
          </div>
          <div className="grid gap-2">
            <Label>{t("filters.status")}</Label>
            <select
              className="h-11 rounded-full border border-border bg-secondary px-4 text-sm"
              value={status}
              onChange={(e) => pushFilters({ status: e.target.value })}
            >
              <option value="all">{t("filters.allStatuses")}</option>
              <option value="running">{t("status.running")}</option>
              <option value="done">{t("status.done")}</option>
              <option value="error">{t("status.error")}</option>
              <option value="lost">{t("status.lost")}</option>
            </select>
          </div>
          <div className="grid gap-2">
            <Label>{t("filters.sort")}</Label>
            <select
              className="h-11 rounded-full border border-border bg-secondary px-4 text-sm"
              value={order}
              onChange={(e) => pushFilters({ order: e.target.value })}
            >
              <option value="desc">{t("filters.newest")}</option>
              <option value="asc">{t("filters.oldest")}</option>
            </select>
          </div>
        </div>
        <div className="mt-4 flex items-center gap-2">
          <Button type="button" variant="outline" className="rounded-full" onClick={() => void loadRuns()} disabled={loading}>
            {loading ? <RefreshCw className="mr-2 size-4 animate-spin" /> : null}
            {t("actions.refresh")}
          </Button>
          <span className="text-sm text-muted-foreground">{t("meta.total", { count: total })}</span>
        </div>
        {error ? <p className="mt-3 text-sm text-destructive">{error}</p> : null}
      </div>

      {rows.length === 0 && !loading ? (
        <div className="rounded-2xl border border-border/80 bg-muted/40 px-6 py-5 text-sm text-muted-foreground">
          {t("empty")}
        </div>
      ) : null}

      <div className="space-y-3">
        {rows.map((row) => {
          const criteria =
            row.kind === "job"
              ? [row.search_query, row.location].filter(Boolean).join(" · ")
              : [t("criteria.limit", { count: row.limit_count }), row.account_label].filter(Boolean).join(" · ");
          const promptsOpen = openPromptId === row.id;
          return (
            <div key={row.id} className="rounded-2xl border border-border bg-card p-5">
              <div className="space-y-1">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex min-w-0 flex-1 flex-wrap items-center gap-2">
                    <span className="font-semibold">{row.search_title}</span>
                    <span className="rounded-full border border-border px-2 py-0.5 text-xs text-muted-foreground">
                      {row.kind === "job" ? t("kind.job") : t("kind.post")}
                    </span>
                    <span
                      className={cn(
                        "rounded-full px-2 py-0.5 text-xs",
                        row.status === "error" || row.status === "lost"
                          ? "bg-destructive/15 text-destructive"
                          : row.status === "done"
                            ? "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300"
                            : "bg-muted text-muted-foreground",
                      )}
                    >
                      {row.status === "running"
                        ? t("status.running")
                        : row.status === "done"
                          ? t("status.done")
                          : row.status === "lost"
                            ? t("status.lost")
                            : row.status === "error"
                              ? t("status.error")
                              : row.status}
                    </span>
                    {row.initiated_by === "admin" ? (
                      <span className="text-xs text-muted-foreground">{t("initiatedByAdmin")}</span>
                    ) : null}
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="shrink-0 rounded-full"
                    onClick={() => setOpenPromptId(promptsOpen ? null : row.id)}
                  >
                    {promptsOpen ? <ChevronUp className="size-4" /> : <ChevronDown className="size-4" />}
                    {t("actions.prompts")}
                  </Button>
                </div>
                <p className="text-sm text-muted-foreground">
                  {row.user_full_name || row.user_id} · {formatDt(row.started_at, locale)}
                </p>
                {criteria ? (
                  <p className="line-clamp-2 text-sm text-foreground/90" title={criteria}>
                    {criteria}
                  </p>
                ) : null}
                <p className="text-sm text-muted-foreground">
                  {t("metrics.line", {
                    fetched: row.fetched_count ?? "—",
                    analyzed: row.analyzed_count ?? "—",
                    matched: row.matched_count ?? "—",
                  })}
                </p>
                {row.error ? <p className="text-sm text-destructive">{row.error}</p> : null}
              </div>
              {promptsOpen ? (
                <div className="mt-4 space-y-3 rounded-xl border border-border/80 bg-muted/30 p-4 text-xs">
                  {row.search_prompt ? (
                    <div>
                      <p className="mb-1 font-medium">{t("prompts.search")}</p>
                      <pre className="whitespace-pre-wrap font-mono">{row.search_prompt}</pre>
                    </div>
                  ) : null}
                  {row.comment_prompt ? (
                    <div>
                      <p className="mb-1 font-medium">{t("prompts.comment")}</p>
                      <pre className="whitespace-pre-wrap font-mono">{row.comment_prompt}</pre>
                    </div>
                  ) : null}
                  {row.filter_prompt ? (
                    <div>
                      <p className="mb-1 font-medium">{t("prompts.filter")}</p>
                      <pre className="whitespace-pre-wrap font-mono">{row.filter_prompt}</pre>
                    </div>
                  ) : null}
                </div>
              ) : null}
            </div>
          );
        })}
      </div>
    </div>
  );
}
