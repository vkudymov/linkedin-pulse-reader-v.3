"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { ChevronDown } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";

import { useRouter } from "@/i18n/navigation";
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
  user_id: string;
  search_title: string;
  search_type_code: string;
  user_full_name: string | null;
};

type ListResponse = { items: PromptRow[]; total: number; limit: number; offset: number };

function fmtDt(value: string | null, locale: "ru" | "en") {
  if (!value) return "—";
  const l = locale === "en" ? "en-US" : "ru-RU";
  return new Date(value).toLocaleString(l, { year: "numeric", month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit" });
}

export function AdminPromptsPanel({
  locale,
  initialUsers = [],
}: {
  locale: "ru" | "en";
  initialUsers?: AdminUserOption[];
}) {
  const t = useTranslations("adminPrompts");
  const router = useRouter();
  const searchParams = useSearchParams();

  const userId = searchParams.get("user_id") || "";
  const type = searchParams.get("type") || "all";
  const role = searchParams.get("role") || "all";
  const q = searchParams.get("q") || "";
  const offset = Number(searchParams.get("offset") || "0") || 0;

  const [users] = useState<AdminUserOption[]>(initialUsers);
  const [rows, setRows] = useState<PromptRow[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [draftById, setDraftById] = useState<Record<string, string>>({});
  const [savingById, setSavingById] = useState<Record<string, boolean>>({});
  const [expandedById, setExpandedById] = useState<Record<string, boolean>>({});

  const queryString = useMemo(() => {
    const p = new URLSearchParams();
    if (userId) p.set("user_id", userId);
    if (type !== "all") p.set("type", type);
    if (role !== "all") p.set("role", role);
    if (q) p.set("q", q);
    p.set("limit", "50");
    if (offset > 0) p.set("offset", String(offset));
    return p.toString();
  }, [userId, type, role, q, offset]);

  const pushFilters = useCallback(
    (patch: Record<string, string>) => {
      const p = new URLSearchParams(searchParams.toString());
      for (const [k, v] of Object.entries(patch)) {
        if (!v || v === "all") p.delete(k);
        else p.set(k, v);
      }
      if (patch.user_id !== undefined) p.delete("offset");
      if (patch.type !== undefined) p.delete("offset");
      if (patch.role !== undefined) p.delete("offset");
      if (patch.q !== undefined) p.delete("offset");
      const query = Object.fromEntries(p.entries());
      router.replace({ pathname: "/admin/prompts", query });
    },
    [router, searchParams],
  );

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await fetch(`/api/admin/prompts?${queryString}`, { cache: "no-store" });
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

  const save = async (row: PromptRow) => {
    const body = draftById[row.id];
    if (typeof body !== "string") return;
    setSavingById((m) => ({ ...m, [row.id]: true }));
    try {
      const resp = await fetch(`/api/admin/prompts/${encodeURIComponent(row.id)}`, {
        method: "PATCH",
        cache: "no-store",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ body }),
      });
      const text = await resp.text().catch(() => "");
      if (!resp.ok) throw new Error(text || t("errors.save"));
      const updated = (text ? (JSON.parse(text) as PromptRow) : null) as PromptRow | null;
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
          <Label>{locale === "en" ? "Role" : "Роль"}</Label>
          <select
            className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
            value={role}
            onChange={(e) => pushFilters({ role: e.target.value })}
          >
            <option value="all">{locale === "en" ? "All" : "Все"}</option>
            <option value="filter">filter</option>
            <option value="search">search</option>
            <option value="comment">comment</option>
          </select>
        </div>

        <div className="min-w-[220px] flex-1">
          <Label>{locale === "en" ? "Body contains" : "Body содержит"}</Label>
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
          const draft = draftById[r.id];
          const saving = Boolean(savingById[r.id]);
          const body = typeof draft === "string" ? draft : r.body;
          const dirty = typeof draft === "string" && draft !== r.body;
          const expanded = expandedById[r.id] === true;
          const roleLabel =
            r.role === "filter"
              ? locale === "en"
                ? "Filter prompt"
                : "Промпт фильтра"
              : r.role === "search"
                ? locale === "en"
                  ? "Search prompt"
                  : "Промпт поиска"
                : r.role === "comment"
                  ? locale === "en"
                    ? "Comment prompt"
                    : "Промпт комментария"
                  : r.role;
          return (
            <div key={r.id} className="rounded-lg border border-border bg-card p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="min-w-0">
                  <div className="text-sm text-muted-foreground">
                    {r.user_full_name || r.user_id} · {r.search_type_code}/{r.role} · {r.id}
                  </div>
                  <div className="mt-1 font-medium">{r.search_title}</div>
                  <div className="mt-1 text-xs text-muted-foreground">
                    {locale === "en" ? "Updated" : "Обновлено"}: {fmtDt(r.updated_at, locale)}
                  </div>
                </div>
                {expanded || dirty ? (
                  <Button onClick={() => save(r)} disabled={!dirty || saving}>
                    {saving ? t("actions.saving") : t("actions.save")}
                  </Button>
                ) : null}
              </div>

              {expanded ? (
                <textarea
                  className="mt-3 w-full rounded-md border border-border bg-background px-3 py-2 font-mono text-xs"
                  rows={8}
                  value={body}
                  onChange={(e) => setDraftById((m) => ({ ...m, [r.id]: e.target.value }))}
                />
              ) : null}

              <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
                <div className="text-xs text-muted-foreground/80">
                  {roleLabel}
                  {dirty ? ` · ${locale === "en" ? "unsaved changes" : "есть черновик"}` : null}
                </div>
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
          );
        })}
      </div>
    </div>
  );
}

