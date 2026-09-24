"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { ChevronDown } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";

import { useRouter } from "@/i18n/navigation";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { DEFAULT_COMMENT_PROMPT, DEFAULT_SEARCH_PROMPT } from "@/lib/defaultPrompts";
import { cn } from "@/lib/utils";

type PromptRole = "filter" | "search" | "comment";

type PromptRow = {
  id: string;
  user_id: string;
  role: PromptRole | string;
  title: string;
  body: string;
  created_at: string | null;
  updated_at: string | null;
};

type ListResponse = { items: PromptRow[]; total: number; limit: number; offset: number };

type Draft = { title?: string; body?: string };

const DEFAULT_FILTER_PROMPT = `Оцени вакансию и верни только JSON:
- match: boolean
- score: integer 0..100
- reason: string

Текст вакансии:
<<<JOB_TEXT>>>`;

function defaultBody(role: PromptRole) {
  if (role === "filter") return DEFAULT_FILTER_PROMPT;
  if (role === "comment") return DEFAULT_COMMENT_PROMPT;
  return DEFAULT_SEARCH_PROMPT;
}

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

export function UserPromptsPanel({ locale }: { locale: "ru" | "en" }) {
  const t = useTranslations("userPrompts");
  const router = useRouter();
  const searchParams = useSearchParams();

  const role = searchParams.get("role") || "all";
  const focusId = searchParams.get("id") || "";
  const q = searchParams.get("q") || "";
  const offset = Number(searchParams.get("offset") || "0") || 0;

  const [rows, setRows] = useState<PromptRow[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [draftById, setDraftById] = useState<Record<string, Draft>>({});
  const [savingById, setSavingById] = useState<Record<string, boolean>>({});
  const [expandedById, setExpandedById] = useState<Record<string, boolean>>({});
  const [createOpen, setCreateOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [createRole, setCreateRole] = useState<PromptRole>("search");
  const [createTitle, setCreateTitle] = useState("");
  const [createBody, setCreateBody] = useState(DEFAULT_SEARCH_PROMPT);

  const queryString = useMemo(() => {
    const p = new URLSearchParams();
    if (focusId) p.set("id", focusId);
    if (role !== "all") p.set("role", role);
    if (q) p.set("q", q);
    p.set("limit", "50");
    if (offset > 0) p.set("offset", String(offset));
    return p.toString();
  }, [focusId, role, q, offset]);

  const pushFilters = useCallback(
    (patch: Record<string, string>) => {
      const p = new URLSearchParams(searchParams.toString());
      for (const [k, v] of Object.entries(patch)) {
        if (!v || v === "all") p.delete(k);
        else p.set(k, v);
      }
      if (patch.role !== undefined) p.delete("offset");
      if (patch.q !== undefined) p.delete("offset");
      p.delete("id");
      const query = Object.fromEntries(p.entries());
      router.replace({ pathname: "/prompts", query });
    },
    [router, searchParams],
  );

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await fetch(`/api/prompts?${queryString}`, { cache: "no-store" });
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

  useEffect(() => {
    if (!focusId) return;
    setExpandedById((m) => ({ ...m, [focusId]: true }));
    const handle = window.setTimeout(() => {
      document.getElementById(`prompt-${focusId}`)?.scrollIntoView({ block: "start", behavior: "smooth" });
    }, 50);
    return () => window.clearTimeout(handle);
  }, [focusId, rows]);

  const onDraft = (id: string, patch: Draft) => {
    setDraftById((m) => ({ ...m, [id]: { ...(m[id] || {}), ...patch } }));
  };

  const save = async (row: PromptRow) => {
    const draft = draftById[row.id];
    if (!draft) return;
    setSavingById((m) => ({ ...m, [row.id]: true }));
    try {
      const resp = await fetch(`/api/prompts/${encodeURIComponent(row.id)}`, {
        method: "PATCH",
        cache: "no-store",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(draft),
      });
      const text = await resp.text().catch(() => "");
      if (!resp.ok) throw new Error(text || t("errors.save"));
      const updated = (text ? (JSON.parse(text) as PromptRow) : null) as PromptRow | null;
      if (updated && updated.id) {
        setRows((current) => current.map((r) => (r.id === updated.id ? updated : r)));
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
      const resp = await fetch("/api/prompts", {
        method: "POST",
        cache: "no-store",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ role: createRole, title: createTitle.trim(), body: createBody }),
      });
      const text = await resp.text().catch(() => "");
      if (!resp.ok) throw new Error(text || t("errors.create"));
      const json = text ? (JSON.parse(text) as { prompt?: PromptRow }) : null;
      if (json?.prompt?.id) {
        setRows((current) => [json.prompt as PromptRow, ...current]);
        setTotal((n) => n + 1);
        setCreateTitle("");
        setCreateBody(defaultBody(createRole));
        setCreateOpen(false);
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t("errors.create"));
    } finally {
      setCreating(false);
    }
  };

  const remove = async (row: PromptRow) => {
    if (!window.confirm(t("deleteConfirm"))) return;
    setSavingById((m) => ({ ...m, [row.id]: true }));
    try {
      const resp = await fetch(`/api/prompts/${encodeURIComponent(row.id)}`, {
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

  const roleLabel = (value: string) => {
    if (value === "filter") return t("roles.filter");
    if (value === "search") return t("roles.search");
    if (value === "comment") return t("roles.comment");
    return value;
  };

  const canCreate = createTitle.trim().length > 0 && createBody.trim().length > 0;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-3">
        <div className="min-w-[160px]">
          <Label>{t("fields.role")}</Label>
          <select
            className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
            value={role}
            onChange={(e) => pushFilters({ role: e.target.value })}
          >
            <option value="all">{locale === "en" ? "All" : "Все"}</option>
            <option value="filter">{t("roles.filter")}</option>
            <option value="search">{t("roles.search")}</option>
            <option value="comment">{t("roles.comment")}</option>
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
              <Label>{t("fields.role")}</Label>
              <select
                className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                value={createRole}
                onChange={(e) => {
                  const next = e.target.value as PromptRole;
                  setCreateRole(next);
                  setCreateBody(defaultBody(next));
                }}
              >
                <option value="filter">{t("roles.filter")}</option>
                <option value="search">{t("roles.search")}</option>
                <option value="comment">{t("roles.comment")}</option>
              </select>
            </div>
            <div>
              <Label>{t("fields.title")}</Label>
              <input
                className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                value={createTitle}
                onChange={(e) => setCreateTitle(e.target.value)}
              />
            </div>
            <div className="md:col-span-2">
              <Label>{t("fields.body")}</Label>
              <textarea
                className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 font-mono text-xs"
                rows={10}
                value={createBody}
                onChange={(e) => setCreateBody(e.target.value)}
              />
            </div>
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
          const title = draft.title ?? r.title;
          const body = draft.body ?? r.body;
          const dirty =
            (typeof draft.title === "string" && draft.title !== r.title) ||
            (typeof draft.body === "string" && draft.body !== r.body);
          const expanded = expandedById[r.id] === true;
          return (
            <div id={`prompt-${r.id}`} key={r.id} className="rounded-lg border border-border bg-card p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="min-w-0">
                  <div className="text-sm text-muted-foreground">{roleLabel(r.role)}</div>
                  <div className="mt-1 font-medium">{r.title}</div>
                  <div className="mt-1 text-xs text-muted-foreground">
                    {locale === "en" ? "Updated" : "Обновлено"}: {fmtDt(r.updated_at, locale)}
                  </div>
                </div>
                {expanded || dirty ? (
                  <Button onClick={() => void save(r)} disabled={!dirty || saving}>
                    {saving ? t("actions.saving") : t("actions.save")}
                  </Button>
                ) : null}
              </div>

              {expanded ? (
                <div className="mt-3 space-y-3">
                  <div>
                    <Label>{t("fields.title")}</Label>
                    <input
                      className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                      value={title}
                      onChange={(e) => onDraft(r.id, { title: e.target.value })}
                    />
                  </div>
                  <textarea
                    className="w-full rounded-md border border-border bg-background px-3 py-2 font-mono text-xs"
                    rows={10}
                    value={body}
                    onChange={(e) => onDraft(r.id, { body: e.target.value })}
                  />
                </div>
              ) : null}

              <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
                <div className="text-xs text-muted-foreground/80">
                  {roleLabel(r.role)}
                  {dirty ? ` · ${locale === "en" ? "unsaved changes" : "есть черновик"}` : null}
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
