"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { ChevronDown } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";

import { Link, useRouter } from "@/i18n/navigation";
import { EmailReportFields } from "@/components/searches/EmailReportFields";
import { PromptPicker, type PromptOption } from "@/components/searches/PromptPicker";
import { SearchRunButton } from "@/components/searches/SearchRunButton";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

type SearchRow = {
  id: string;
  user_id: string;
  search_type_code: "jobs" | "posts" | string;
  title: string;
  status: string;
  last_run_at: string | null;
  search_query: string | null;
  location: string | null;
  account_label: string | null;
  filter_prompt_id: string | null;
  search_prompt_id: string | null;
  comment_prompt_id: string | null;
  filter_prompt: string | null;
  search_prompt: string | null;
  comment_prompt: string | null;
  email_report_enabled?: boolean;
  email_report_format?: string | null;
  created_at: string | null;
  updated_at: string | null;
};

type ListResponse = { items: SearchRow[]; total: number; limit: number; offset: number };
type PromptsResponse = { items: PromptOption[] };

type CreateDraft = {
  type: "jobs" | "posts";
  title: string;
  status: "active" | "paused";
  search_query: string;
  location: string;
  account_label: string;
  filter_prompt_id: string;
  search_prompt_id: string;
  comment_prompt_id: string;
};

const EMPTY_CREATE: CreateDraft = {
  type: "posts",
  title: "",
  status: "active",
  search_query: "",
  location: "",
  account_label: "",
  filter_prompt_id: "",
  search_prompt_id: "",
  comment_prompt_id: "",
};

function fmtDt(value: string | null, locale: "ru" | "en") {
  if (!value) return "—";
  const l = locale === "en" ? "en-US" : "ru-RU";
  return new Date(value).toLocaleString(l, {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function UserSearchesPanel({ locale }: { locale: "ru" | "en" }) {
  const t = useTranslations("userSearches");
  const router = useRouter();
  const searchParams = useSearchParams();

  const type = searchParams.get("type") || "all";
  const status = searchParams.get("status") || "all";
  const q = searchParams.get("q") || "";
  const offset = Number(searchParams.get("offset") || "0") || 0;

  const [rows, setRows] = useState<SearchRow[]>([]);
  const [prompts, setPrompts] = useState<PromptOption[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savingById, setSavingById] = useState<Record<string, boolean>>({});
  const [draftById, setDraftById] = useState<Record<string, Partial<SearchRow>>>({});
  const [expandedById, setExpandedById] = useState<Record<string, boolean>>({});
  const [createOpen, setCreateOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [createDraft, setCreateDraft] = useState<CreateDraft>(EMPTY_CREATE);

  const queryString = useMemo(() => {
    const p = new URLSearchParams();
    if (type !== "all") p.set("type", type);
    if (status !== "all") p.set("status", status);
    if (q) p.set("q", q);
    p.set("limit", "50");
    if (offset > 0) p.set("offset", String(offset));
    return p.toString();
  }, [type, status, q, offset]);

  const pushFilters = useCallback(
    (patch: Record<string, string>) => {
      const p = new URLSearchParams(searchParams.toString());
      for (const [k, v] of Object.entries(patch)) {
        if (!v || v === "all") p.delete(k);
        else p.set(k, v);
      }
      if (patch.type !== undefined) p.delete("offset");
      if (patch.status !== undefined) p.delete("offset");
      if (patch.q !== undefined) p.delete("offset");
      const query = Object.fromEntries(p.entries());
      router.replace({ pathname: "/searches", query });
    },
    [router, searchParams],
  );

  const loadPrompts = useCallback(async () => {
    const resp = await fetch("/api/prompts?limit=200", { cache: "no-store" });
    const text = await resp.text().catch(() => "");
    if (!resp.ok) throw new Error(text || t("errors.load"));
    const json = (text ? (JSON.parse(text) as PromptsResponse) : null) as PromptsResponse | null;
    setPrompts(Array.isArray(json?.items) ? json!.items : []);
  }, [t]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [searchesResp] = await Promise.all([
        fetch(`/api/searches?${queryString}`, { cache: "no-store" }),
        loadPrompts(),
      ]);
      const text = await searchesResp.text().catch(() => "");
      if (!searchesResp.ok) throw new Error(text || t("errors.load"));
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
  }, [loadPrompts, queryString, t]);

  useEffect(() => {
    const handle = window.setTimeout(() => {
      void load();
    }, 0);
    return () => window.clearTimeout(handle);
  }, [load]);

  const promptsByRole = useMemo(() => {
    const filter = prompts.filter((p) => p.role === "filter");
    const search = prompts.filter((p) => p.role === "search");
    const comment = prompts.filter((p) => p.role === "comment");
    return { filter, search, comment };
  }, [prompts]);

  const onDraft = (id: string, patch: Partial<SearchRow>) => {
    setDraftById((m) => ({ ...m, [id]: { ...(m[id] || {}), ...patch } }));
  };

  const save = async (row: SearchRow) => {
    setSavingById((m) => ({ ...m, [row.id]: true }));
    try {
      const patch = draftById[row.id] || {};
      const resp = await fetch(`/api/searches/${encodeURIComponent(row.id)}`, {
        method: "PATCH",
        cache: "no-store",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(patch),
      });
      const text = await resp.text().catch(() => "");
      if (!resp.ok) throw new Error(text || t("errors.save"));
      const updated = (text ? (JSON.parse(text) as SearchRow) : null) as SearchRow | null;
      if (updated && updated.id) {
        setRows((current) => current.map((r) => (r.id === updated.id ? { ...r, ...updated } : r)));
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

  const create = async () => {
    setCreating(true);
    setError(null);
    try {
      const payload: Record<string, unknown> = {
        type: createDraft.type,
        title: createDraft.title.trim(),
        status: createDraft.status,
      };
      if (createDraft.type === "jobs") {
        payload.search_query = createDraft.search_query.trim();
        payload.location = createDraft.location.trim();
        payload.filter_prompt_id = createDraft.filter_prompt_id;
      } else {
        payload.search_prompt_id = createDraft.search_prompt_id;
        payload.comment_prompt_id = createDraft.comment_prompt_id || null;
        payload.account_label = createDraft.account_label.trim();
      }
      const resp = await fetch("/api/searches", {
        method: "POST",
        cache: "no-store",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(payload),
      });
      const text = await resp.text().catch(() => "");
      if (!resp.ok) throw new Error(text || t("errors.create"));
      const json = text ? (JSON.parse(text) as { search?: SearchRow }) : null;
      if (json?.search?.id) {
        setRows((current) => [json.search as SearchRow, ...current]);
        setTotal((n) => n + 1);
        setCreateDraft(EMPTY_CREATE);
        setCreateOpen(false);
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t("errors.create"));
    } finally {
      setCreating(false);
    }
  };

  const remove = async (row: SearchRow) => {
    if (!window.confirm(t("deleteConfirm"))) return;
    setSavingById((m) => ({ ...m, [row.id]: true }));
    try {
      const resp = await fetch(`/api/searches/${encodeURIComponent(row.id)}`, {
        method: "DELETE",
        cache: "no-store",
      });
      const text = await resp.text().catch(() => "");
      if (!resp.ok) throw new Error(text || t("errors.delete"));
      setRows((current) => current.filter((r) => r.id !== row.id));
      setTotal((n) => Math.max(0, n - 1));
      setDraftById((m) => {
        const next = { ...m };
        delete next[row.id];
        return next;
      });
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t("errors.delete"));
    } finally {
      setSavingById((m) => ({ ...m, [row.id]: false }));
    }
  };

  const canCreate =
    createDraft.title.trim().length > 0 &&
    (createDraft.type === "jobs"
      ? createDraft.search_query.trim().length > 0 && Boolean(createDraft.filter_prompt_id)
      : Boolean(createDraft.search_prompt_id));

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-3">
        <div className="min-w-[160px]">
          <Label>{t("fields.type")}</Label>
          <select
            className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
            value={type}
            onChange={(e) => pushFilters({ type: e.target.value })}
          >
            <option value="all">{locale === "en" ? "All" : "Все"}</option>
            <option value="jobs">{t("types.jobs")}</option>
            <option value="posts">{t("types.posts")}</option>
          </select>
        </div>

        <div className="min-w-[160px]">
          <Label>{t("fields.status")}</Label>
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
          <Label>{t("fields.title")}</Label>
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
        <Button type="button" onClick={() => setCreateOpen((v) => !v)}>
          {t("createTitle")}
        </Button>
      </div>

      {createOpen ? (
        <div className="rounded-lg border border-border bg-card p-4">
          <div className="mb-3 font-medium">{t("createTitle")}</div>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <div>
              <Label>{t("fields.type")}</Label>
              <select
                className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                value={createDraft.type}
                onChange={(e) =>
                  setCreateDraft((d) => ({ ...d, type: e.target.value === "jobs" ? "jobs" : "posts" }))
                }
              >
                <option value="posts">{t("types.posts")}</option>
                <option value="jobs">{t("types.jobs")}</option>
              </select>
            </div>
            <div>
              <Label>{t("fields.title")}</Label>
              <input
                className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                value={createDraft.title}
                onChange={(e) => setCreateDraft((d) => ({ ...d, title: e.target.value }))}
              />
            </div>
            {createDraft.type === "jobs" ? (
              <>
                <div>
                  <Label>{t("fields.searchQuery")}</Label>
                  <input
                    className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                    value={createDraft.search_query}
                    onChange={(e) => setCreateDraft((d) => ({ ...d, search_query: e.target.value }))}
                  />
                </div>
                <div>
                  <Label>{t("fields.location")}</Label>
                  <input
                    className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                    value={createDraft.location}
                    onChange={(e) => setCreateDraft((d) => ({ ...d, location: e.target.value }))}
                  />
                </div>
                <PromptPicker
                  label={t("fields.filterPrompt")}
                  value={createDraft.filter_prompt_id}
                  options={promptsByRole.filter}
                  emptyLabel={t("fields.noPrompt")}
                  editLabel={t("actions.editPrompt")}
                  onChange={(id) => setCreateDraft((d) => ({ ...d, filter_prompt_id: id }))}
                />
                {promptsByRole.filter.length === 0 ? (
                  <div className="md:col-span-2 text-xs text-muted-foreground">
                    <Link href="/prompts" className="underline underline-offset-4">
                      {locale === "en" ? "Create a filter prompt first." : "Сначала создай промпт фильтра."}
                    </Link>
                  </div>
                ) : null}
              </>
            ) : (
              <>
                <div>
                  <Label>{t("fields.account")}</Label>
                  <input
                    className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                    value={createDraft.account_label}
                    onChange={(e) => setCreateDraft((d) => ({ ...d, account_label: e.target.value }))}
                  />
                </div>
                <PromptPicker
                  label={t("fields.searchPrompt")}
                  value={createDraft.search_prompt_id}
                  options={promptsByRole.search}
                  emptyLabel={t("fields.noPrompt")}
                  editLabel={t("actions.editPrompt")}
                  onChange={(id) => setCreateDraft((d) => ({ ...d, search_prompt_id: id }))}
                />
                {promptsByRole.search.length === 0 ? (
                  <div className="md:col-span-2 text-xs text-muted-foreground">
                    <Link href="/prompts" className="underline underline-offset-4">
                      {locale === "en" ? "Create a search prompt first." : "Сначала создай промпт поиска."}
                    </Link>
                  </div>
                ) : null}
                <PromptPicker
                  label={t("fields.commentPrompt")}
                  value={createDraft.comment_prompt_id}
                  options={promptsByRole.comment}
                  emptyLabel={t("fields.noPrompt")}
                  editLabel={t("actions.editPrompt")}
                  onChange={(id) => setCreateDraft((d) => ({ ...d, comment_prompt_id: id }))}
                />
              </>
            )}
          </div>
          <div className="mt-4">
            <Button onClick={() => void create()} disabled={!canCreate || creating}>
              {creating ? t("actions.creating") : t("actions.create")}
            </Button>
          </div>
        </div>
      ) : null}

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
          const typeLabel = r.search_type_code === "jobs" ? t("types.jobs") : t("types.posts");
          return (
            <div key={r.id} className="rounded-lg border border-border bg-card p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="min-w-0">
                  <div className="text-sm text-muted-foreground">
                    {typeLabel} · {r.status}
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
                    disabled={saving}
                    onDone={() => void load()}
                  />
                  {expanded || hasDraft ? (
                    <Button onClick={() => void save(r)} disabled={!hasDraft || saving}>
                      {saving ? t("actions.saving") : t("actions.save")}
                    </Button>
                  ) : null}
                </div>
              </div>

              {expanded ? (
                <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
                  <div>
                    <Label>{t("fields.title")}</Label>
                    <input
                      className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                      value={(draft.title ?? r.title) as string}
                      onChange={(e) => onDraft(r.id, { title: e.target.value })}
                    />
                  </div>
                  <div>
                    <Label>{t("fields.status")}</Label>
                    <select
                      className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                      value={(draft.status ?? r.status) as string}
                      onChange={(e) => onDraft(r.id, { status: e.target.value })}
                    >
                      <option value="active">{locale === "en" ? "Active" : "Активен"}</option>
                      <option value="paused">{locale === "en" ? "Paused" : "Пауза"}</option>
                    </select>
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
                        <Label>{t("fields.searchQuery")}</Label>
                        <input
                          className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                          value={((draft.search_query ?? r.search_query) || "") as string}
                          onChange={(e) => onDraft(r.id, { search_query: e.target.value })}
                        />
                      </div>
                      <div>
                        <Label>{t("fields.location")}</Label>
                        <input
                          className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                          value={((draft.location ?? r.location) || "") as string}
                          onChange={(e) => onDraft(r.id, { location: e.target.value || null })}
                        />
                      </div>
                      <PromptPicker
                        label={t("fields.filterPrompt")}
                        value={((draft.filter_prompt_id ?? r.filter_prompt_id) || "") as string}
                        options={promptsByRole.filter}
                        fallbackBody={r.filter_prompt}
                        emptyLabel={t("fields.noPrompt")}
                        editLabel={t("actions.editPrompt")}
                        onChange={(id) => onDraft(r.id, { filter_prompt_id: id })}
                      />
                    </>
                  ) : (
                    <>
                      <div>
                        <Label>{t("fields.account")}</Label>
                        <input
                          className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                          value={((draft.account_label ?? r.account_label) || "") as string}
                          onChange={(e) => onDraft(r.id, { account_label: e.target.value || null })}
                        />
                      </div>
                      <PromptPicker
                        label={t("fields.searchPrompt")}
                        value={((draft.search_prompt_id ?? r.search_prompt_id) || "") as string}
                        options={promptsByRole.search}
                        fallbackBody={r.search_prompt}
                        emptyLabel={t("fields.noPrompt")}
                        editLabel={t("actions.editPrompt")}
                        onChange={(id) => onDraft(r.id, { search_prompt_id: id })}
                      />
                      <PromptPicker
                        label={t("fields.commentPrompt")}
                        value={((draft.comment_prompt_id ?? r.comment_prompt_id) || "") as string}
                        options={promptsByRole.comment}
                        fallbackBody={r.comment_prompt}
                        emptyLabel={t("fields.noPrompt")}
                        editLabel={t("actions.editPrompt")}
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
                      {typeLabel}
                      {hasDraft ? ` · ${locale === "en" ? "unsaved changes" : "есть черновик"}` : null}
                    </span>
                  )}
                </div>
                <div className="flex gap-2">
                  {expanded ? (
                    <Button type="button" variant="outline" size="sm" onClick={() => void remove(r)} disabled={saving}>
                      {t("actions.delete")}
                    </Button>
                  ) : null}
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="shrink-0"
                    onClick={() => setExpandedById((m) => ({ ...m, [r.id]: !expanded }))}
                  >
                    <ChevronDown className={cn("size-4 transition-transform", expanded && "rotate-180")} />
                    {expanded ? t("actions.collapse") : t("actions.expand")}
                  </Button>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
