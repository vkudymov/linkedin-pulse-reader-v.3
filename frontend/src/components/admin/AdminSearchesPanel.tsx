"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { ChevronDown } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";

import { useRouter } from "@/i18n/navigation";
import { EmailReportFields } from "@/components/searches/EmailReportFields";
import { PromptPicker, type PromptOption } from "@/components/searches/PromptPicker";
import { SearchRunButton } from "@/components/searches/SearchRunButton";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import type { AdminUserOption } from "@/lib/admin/users";
import { cn } from "@/lib/utils";

type PromptRow = {
  id: string;
  search_id: string;
  role: string;
  body: string;
  created_at: string | null;
  updated_at: string | null;
};

type SearchRow = {
  id: string;
  user_id: string;
  search_type_code: "jobs" | "posts" | string;
  title: string;
  status: string;
  last_run_at: string | null;
  search_tariff_id: string | null;
  email_report_enabled: boolean;
  email_report_format: string;
  search_query: string | null;
  location: string | null;
  linkedin_filters: unknown;
  account_label: string | null;
  filter_prompt_id: string | null;
  search_prompt_id: string | null;
  comment_prompt_id: string | null;
  filter_prompt: string | null;
  search_prompt: string | null;
  comment_prompt: string | null;
  prompts: PromptRow[];
  user_full_name: string | null;
  created_at: string | null;
  updated_at: string | null;
};

type ListResponse = { items: SearchRow[]; total: number; limit: number; offset: number };

function fmtDt(value: string | null, locale: "ru" | "en") {
  if (!value) return "—";
  const l = locale === "en" ? "en-US" : "ru-RU";
  return new Date(value).toLocaleString(l, { year: "numeric", month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit" });
}

export function AdminSearchesPanel({
  locale,
  initialUsers = [],
}: {
  locale: "ru" | "en";
  initialUsers?: AdminUserOption[];
}) {
  const t = useTranslations("adminSearches");
  const router = useRouter();
  const searchParams = useSearchParams();

  const userId = searchParams.get("user_id") || "";
  const type = searchParams.get("type") || "all";
  const status = searchParams.get("status") || "all";
  const q = searchParams.get("q") || "";
  const orderBy = searchParams.get("order_by") || "created_at";
  const order = searchParams.get("order") || "desc";
  const offset = Number(searchParams.get("offset") || "0") || 0;

  const [users] = useState<AdminUserOption[]>(initialUsers);
  const [rows, setRows] = useState<SearchRow[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savingById, setSavingById] = useState<Record<string, boolean>>({});
  const [draftById, setDraftById] = useState<Record<string, Partial<SearchRow>>>({});
  const [expandedById, setExpandedById] = useState<Record<string, boolean>>({});
  const [promptsByUserId, setPromptsByUserId] = useState<Record<string, PromptOption[]>>({});
  const [promptsLoadingByUserId, setPromptsLoadingByUserId] = useState<Record<string, boolean>>({});

  const queryString = useMemo(() => {
    const p = new URLSearchParams();
    if (userId) p.set("user_id", userId);
    if (type !== "all") p.set("type", type);
    if (status !== "all") p.set("status", status);
    if (q) p.set("q", q);
    if (orderBy && orderBy !== "created_at") p.set("order_by", orderBy);
    if (order === "asc") p.set("order", "asc");
    p.set("limit", "50");
    if (offset > 0) p.set("offset", String(offset));
    return p.toString();
  }, [userId, type, status, q, orderBy, order, offset]);

  const pushFilters = useCallback(
    (patch: Record<string, string>) => {
      const p = new URLSearchParams(searchParams.toString());
      for (const [k, v] of Object.entries(patch)) {
        if (!v || v === "all") p.delete(k);
        else p.set(k, v);
      }
      if (patch.user_id !== undefined) p.delete("offset");
      if (patch.type !== undefined) p.delete("offset");
      if (patch.status !== undefined) p.delete("offset");
      if (patch.q !== undefined) p.delete("offset");
      const query = Object.fromEntries(p.entries());
      router.replace({ pathname: "/admin/searches", query });
    },
    [router, searchParams],
  );

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await fetch(`/api/admin/searches?${queryString}`, { cache: "no-store" });
      const text = await resp.text().catch(() => "");
      if (!resp.ok) throw new Error(text || t("errors.load"));
      const json = (text ? (JSON.parse(text) as ListResponse) : null) as ListResponse | null;
      setRows(Array.isArray(json?.items) ? json!.items : []);
      setTotal(typeof json?.total === "number" ? json.total : 0);
    } catch (e: unknown) {
      setRows([]);
      setTotal(0);
      setError(e instanceof Error ? e.message : t("errors.load"));
    } finally {
      setLoading(false);
    }
  }, [queryString, t]);

  useEffect(() => {
    const handle = window.setTimeout(() => {
      void load();
    }, 0);
    return () => window.clearTimeout(handle);
  }, [load]);

  const onDraft = (id: string, patch: Partial<SearchRow>) => {
    setDraftById((m) => ({ ...m, [id]: { ...(m[id] || {}), ...patch } }));
  };

  const loadPromptsForUser = useCallback(async (uid: string) => {
    if (!uid || uid in promptsByUserId || promptsLoadingByUserId[uid]) return;
    setPromptsLoadingByUserId((m) => ({ ...m, [uid]: true }));
    try {
      const resp = await fetch(`/api/admin/prompts?user_id=${encodeURIComponent(uid)}&limit=200`, {
        cache: "no-store",
      });
      const text = await resp.text().catch(() => "");
      if (!resp.ok) throw new Error(text || t("errors.load"));
      const json = text ? (JSON.parse(text) as { items?: PromptOption[] }) : null;
      setPromptsByUserId((m) => ({ ...m, [uid]: Array.isArray(json?.items) ? json!.items : [] }));
    } catch {
      setPromptsByUserId((m) => ({ ...m, [uid]: [] }));
    } finally {
      setPromptsLoadingByUserId((m) => ({ ...m, [uid]: false }));
    }
  }, [promptsByUserId, promptsLoadingByUserId, t]);

  const save = async (row: SearchRow) => {
    setSavingById((m) => ({ ...m, [row.id]: true }));
    try {
      const patch = draftById[row.id] || {};
      const resp = await fetch(`/api/admin/searches/${encodeURIComponent(row.id)}`, {
        method: "PATCH",
        cache: "no-store",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(patch),
      });
      const text = await resp.text().catch(() => "");
      if (!resp.ok) throw new Error(text || t("errors.save"));
      const updated = (text ? (JSON.parse(text) as SearchRow) : null) as SearchRow | null;
      if (updated && updated.id) {
        setRows((rows) => rows.map((r) => (r.id === updated.id ? updated : r)));
        setDraftById((m) => {
          const next = { ...m };
          delete next[row.id];
          return next;
        });
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t("errors.save"));
    } finally {
      setSavingById((m) => ({ ...m, [row.id]: false }));
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-3">
        <div className="min-w-[220px]">
          <Label>{locale === "en" ? "User" : "Пользователь"}</Label>
          <select
            className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
            value={userId || "all"}
            onChange={(e) => pushFilters({ user_id: e.target.value === "all" ? "" : e.target.value })}
          >
            <option value="all">{locale === "en" ? "All users" : "Все пользователи"}</option>
            {users.map((u) => (
              <option key={u.id} value={u.id}>
                {(u.full_name || u.email || u.id).slice(0, 80)}
              </option>
            ))}
          </select>
        </div>

        <div className="min-w-[160px]">
          <Label>{locale === "en" ? "Type" : "Тип"}</Label>
          <select
            className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
            value={type}
            onChange={(e) => pushFilters({ type: e.target.value })}
          >
            <option value="all">{locale === "en" ? "All" : "Все"}</option>
            <option value="jobs">{locale === "en" ? "Jobs" : "Вакансии"}</option>
            <option value="posts">{locale === "en" ? "Posts" : "Посты"}</option>
          </select>
        </div>

        <div className="min-w-[160px]">
          <Label>{locale === "en" ? "Status" : "Статус"}</Label>
          <select
            className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
            value={status}
            onChange={(e) => pushFilters({ status: e.target.value })}
          >
            <option value="all">{locale === "en" ? "All" : "Все"}</option>
            <option value="active">{locale === "en" ? "Active" : "Активен"}</option>
            <option value="paused">{locale === "en" ? "Paused" : "Пауза"}</option>
          </select>
        </div>

        <div className="min-w-[220px] flex-1">
          <Label>{locale === "en" ? "Title contains" : "Title содержит"}</Label>
          <input
            className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
            value={q}
            onChange={(e) => pushFilters({ q: e.target.value })}
            placeholder={locale === "en" ? "Text..." : "Текст..."}
          />
        </div>

        <Button variant="outline" onClick={load} disabled={loading}>
          {t("actions.refresh")}
        </Button>
      </div>

      {error ? <div className="rounded-md border border-destructive/40 bg-destructive/5 p-3 text-sm">{error}</div> : null}

      {rows.length === 0 && !loading ? <div className="text-sm text-muted-foreground">{t("empty")}</div> : null}

      <div className="text-xs text-muted-foreground">
        {locale === "en" ? `Total: ${total}` : `Всего: ${total}`}
      </div>

      <div className="space-y-3">
        {rows.map((r) => {
          const draft = draftById[r.id] || {};
          const saving = Boolean(savingById[r.id]);
          const hasDraft = Object.keys(draft).length > 0;
          const expanded = expandedById[r.id] === true;
          return (
            <div key={r.id} className="rounded-lg border border-border bg-card p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="min-w-0">
                  <div className="text-sm text-muted-foreground">
                    {r.user_full_name || r.user_id} ·{" "}
                    {r.search_type_code === "jobs"
                      ? locale === "en"
                        ? "Jobs"
                        : "Вакансии"
                      : locale === "en"
                        ? "Posts"
                        : "Посты"}{" "}
                    · {r.id}
                  </div>
                  <div className="mt-1 font-medium">{r.title}</div>
                  <div className="mt-1 text-xs text-muted-foreground">
                    {locale === "en" ? "Created" : "Создан"}: {fmtDt(r.created_at, locale)} ·{" "}
                    {locale === "en" ? "Last run" : "Последний запуск"}: {fmtDt(r.last_run_at, locale)}
                  </div>
                </div>
                <div className="flex flex-wrap items-start justify-end gap-2">
                  <SearchRunButton
                    kind={r.search_type_code === "jobs" ? "jobs" : "posts"}
                    searchId={r.id}
                    userId={r.user_id}
                    disabled={saving}
                    onDone={() => void load()}
                  />
                  {expanded || hasDraft ? (
                    <Button onClick={() => save(r)} disabled={!hasDraft || saving}>
                      {saving ? t("actions.saving") : t("actions.save")}
                    </Button>
                  ) : null}
                </div>
              </div>

              {expanded ? (
              <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
                <div>
                  <Label>{locale === "en" ? "Title" : "Название"}</Label>
                  <input
                    className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                    value={(draft.title ?? r.title) as string}
                    onChange={(e) => onDraft(r.id, { title: e.target.value })}
                  />
                </div>
                <div>
                  <Label>{locale === "en" ? "Status" : "Статус"}</Label>
                  <select
                    className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                    value={(draft.status ?? r.status) as string}
                    onChange={(e) => onDraft(r.id, { status: e.target.value })}
                  >
                    <option value="active">{locale === "en" ? "Active" : "Активен"}</option>
                    <option value="paused">{locale === "en" ? "Paused" : "Пауза"}</option>
                  </select>
                </div>

                <div>
                  <Label>{locale === "en" ? "Tariff id" : "Tariff id"}</Label>
                  <input
                    className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                    value={((draft.search_tariff_id ?? r.search_tariff_id) || "") as string}
                    onChange={(e) => onDraft(r.id, { search_tariff_id: e.target.value || null })}
                    placeholder="uuid or empty"
                  />
                </div>
                <EmailReportFields
                  enabled={Boolean(draft.email_report_enabled ?? r.email_report_enabled)}
                  format={String(draft.email_report_format ?? r.email_report_format ?? "none")}
                  onEnabledChange={(enabled) => onDraft(r.id, { email_report_enabled: enabled })}
                  onFormatChange={(format) => onDraft(r.id, { email_report_format: format })}
                />

                {r.search_type_code === "jobs" ? (
                  <>
                    <div>
                      <Label>{locale === "en" ? "Search query" : "Search query"}</Label>
                      <input
                        className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                        value={((draft.search_query ?? r.search_query) || "") as string}
                        onChange={(e) => onDraft(r.id, { search_query: e.target.value })}
                      />
                    </div>
                    <div>
                      <Label>{locale === "en" ? "Location" : "Локация"}</Label>
                      <input
                        className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                        value={((draft.location ?? r.location) || "") as string}
                        onChange={(e) => onDraft(r.id, { location: e.target.value || null })}
                      />
                    </div>
                    <PromptPicker
                      label={locale === "en" ? "Filter prompt" : "Промпт фильтра"}
                      value={((draft.filter_prompt_id ?? r.filter_prompt_id) || "") as string}
                      options={(promptsByUserId[r.user_id] || []).filter((p) => p.role === "filter")}
                      fallbackBody={r.filter_prompt}
                      emptyLabel={locale === "en" ? "Not selected" : "Не выбран"}
                      loading={Boolean(promptsLoadingByUserId[r.user_id])}
                      editLabel={locale === "en" ? "Open in Prompts" : "Открыть в Промптах"}
                      editHref={{ pathname: "/admin/prompts", query: { user_id: r.user_id } }}
                      onChange={(id) => onDraft(r.id, { filter_prompt_id: id || null })}
                    />
                    <div className="md:col-span-2">
                      <Label>{locale === "en" ? "LinkedIn filters (JSON)" : "LinkedIn filters (JSON)"}</Label>
                      <textarea
                        className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 font-mono text-xs"
                        rows={3}
                        value={JSON.stringify(draft.linkedin_filters ?? r.linkedin_filters ?? {}, null, 2)}
                        onChange={(e) => {
                          try {
                            onDraft(r.id, { linkedin_filters: JSON.parse(e.target.value) });
                          } catch {
                            // ignore invalid JSON until user fixes it; do not overwrite
                          }
                        }}
                      />
                    </div>
                  </>
                ) : (
                  <>
                    <div>
                      <Label>{locale === "en" ? "Account label" : "Аккаунт"}</Label>
                      <input
                        className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                        value={((draft.account_label ?? r.account_label) || "") as string}
                        onChange={(e) => onDraft(r.id, { account_label: e.target.value || null })}
                      />
                    </div>
                    <PromptPicker
                      label={locale === "en" ? "Search prompt" : "Промпт поиска"}
                      value={((draft.search_prompt_id ?? r.search_prompt_id) || "") as string}
                      options={(promptsByUserId[r.user_id] || []).filter((p) => p.role === "search")}
                      fallbackBody={r.search_prompt}
                      emptyLabel={locale === "en" ? "Not selected" : "Не выбран"}
                      loading={Boolean(promptsLoadingByUserId[r.user_id])}
                      editLabel={locale === "en" ? "Open in Prompts" : "Открыть в Промптах"}
                      editHref={{ pathname: "/admin/prompts", query: { user_id: r.user_id } }}
                      onChange={(id) => onDraft(r.id, { search_prompt_id: id })}
                    />
                    <PromptPicker
                      label={locale === "en" ? "Comment prompt" : "Промпт комментария"}
                      value={((draft.comment_prompt_id ?? r.comment_prompt_id) || "") as string}
                      options={(promptsByUserId[r.user_id] || []).filter((p) => p.role === "comment")}
                      fallbackBody={r.comment_prompt}
                      emptyLabel={locale === "en" ? "Not selected" : "Не выбран"}
                      loading={Boolean(promptsLoadingByUserId[r.user_id])}
                      editLabel={locale === "en" ? "Open in Prompts" : "Открыть в Промптах"}
                      editHref={{ pathname: "/admin/prompts", query: { user_id: r.user_id } }}
                      onChange={(id) => onDraft(r.id, { comment_prompt_id: id || null })}
                    />
                  </>
                )}
              </div>
              ) : null}

              <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
                <div className={cn("text-xs text-muted-foreground", hasDraft && expanded ? "" : "opacity-70")}>
                  {expanded ? (
                    <>
                      {locale === "en" ? "Draft fields:" : "Черновик полей:"}{" "}
                      {Object.keys(draft).join(", ") || "—"}
                    </>
                  ) : (
                    <span className="text-muted-foreground/80">
                      {r.search_type_code === "jobs"
                        ? locale === "en"
                          ? "Job search"
                          : "Поиск вакансий"
                        : locale === "en"
                          ? "Post search"
                          : "Поиск постов"}
                      {hasDraft ? ` · ${locale === "en" ? "unsaved changes" : "есть черновик"}` : null}
                    </span>
                  )}
                </div>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="shrink-0"
                  onClick={() => {
                    const next = !expanded;
                    setExpandedById((m) => ({ ...m, [r.id]: next }));
                    if (next) void loadPromptsForUser(r.user_id);
                  }}
                >
                  <ChevronDown className={cn("size-4 transition-transform", expanded && "rotate-180")} />
                  {expanded ? t("actions.collapse") : t("actions.expand")}
                </Button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

