"use client";

import { useEffect, useMemo, useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import { useTranslations } from "next-intl";

import { AllFiltersDialog } from "@/components/people/AllFiltersDialog";
import { PeopleSearchRunButton } from "@/components/people/PeopleSearchRunButton";
import { SearchTariffSummary } from "@/components/SearchTariffSummary";
import { PromptPicker, type PromptOption } from "@/components/searches/PromptPicker";
import { Button, buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { normalizeBooleanQuery } from "@/lib/booleanQuery";
import { DEFAULT_PEOPLE_PROMPT, PEOPLE_REQUIRED_MARKER } from "@/lib/defaultPrompts";
import {
  DEFAULT_PEOPLE_FILTERS,
  normalizePeopleFilters,
  peopleFiltersActiveCount,
  type PeopleFilters,
} from "@/lib/peopleFilters";
import type { SearchTariffInfo } from "@/lib/searchTariffs";
import { cn } from "@/lib/utils";

export type PeopleSearchDto = {
  id: string;
  title: string;
  search_query: string;
  people_prompt: string;
  people_prompt_id?: string | null;
  status: "active" | "paused" | string;
  last_run_at: string | null;
  linkedin_filters?: PeopleFilters | Record<string, unknown> | null;
  new_match_count?: number;
  target_found_count?: number;
  search_tariff_id?: string | null;
  search_tariff?: SearchTariffInfo | null;
};

function BooleanHint({ query }: { query: string }) {
  const t = useTranslations("people.boolean");
  const result = useMemo(() => normalizeBooleanQuery(query), [query]);
  return (
    <div className="space-y-1 text-xs">
      <p className="text-muted-foreground">{t("hint")}</p>
      {result.warnings.map((w) => (
        <p key={w} className="text-amber-600 dark:text-amber-300">
          {w === "LinkedIn does not support + or -; use AND / NOT instead" ? t("plusMinus") : w}
        </p>
      ))}
      {result.errors.map((err) => (
        <p key={err} className="text-destructive">
          {err === "unbalanced quotes"
            ? t("unbalancedQuotes")
            : err === "unbalanced parentheses"
              ? t("unbalancedParens")
              : err === "query cannot start with AND/OR"
                ? t("startsWithOp")
                : err === "query cannot end with AND/OR/NOT"
                  ? t("endsWithOp")
                  : err}
        </p>
      ))}
    </div>
  );
}

export function PeopleSearchesPanel({ initial }: { initial: PeopleSearchDto[] }) {
  const t = useTranslations("people.prompts");
  const [items, setItems] = useState<PeopleSearchDto[]>(initial);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [prompts, setPrompts] = useState<PromptOption[]>([]);
  const [title, setTitle] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [peoplePromptId, setPeoplePromptId] = useState("");
  const [peoplePrompt, setPeoplePrompt] = useState(`${DEFAULT_PEOPLE_PROMPT}\n`);
  const [linkedinFilters, setLinkedinFilters] = useState<PeopleFilters>(DEFAULT_PEOPLE_FILTERS);
  const [filtersOpen, setFiltersOpen] = useState(false);

  const selectedPrompt = prompts.find((p) => p.id === peoplePromptId);
  const boolean = normalizeBooleanQuery(searchQuery);
  const canCreate = useMemo(() => {
    const body = selectedPrompt?.body || peoplePrompt;
    return (
      title.trim().length > 0 &&
      searchQuery.trim().length > 0 &&
      boolean.ok &&
      body.trim().length > 0 &&
      body.includes(PEOPLE_REQUIRED_MARKER)
    );
  }, [title, searchQuery, boolean.ok, selectedPrompt, peoplePrompt]);

  useEffect(() => {
    void (async () => {
      const resp = await fetch("/api/prompts?role=people&limit=100");
      const json = (await resp.json().catch(() => null)) as { items?: PromptOption[] } | null;
      if (resp.ok && Array.isArray(json?.items)) setPrompts(json.items);
    })();
  }, []);

  async function refresh() {
    const resp = await fetch("/api/people-searches", { method: "GET" });
    const json = (await resp.json().catch(() => null)) as
      | { ok?: boolean; people_searches?: PeopleSearchDto[] }
      | null;
    if (!resp.ok || !json?.ok || !Array.isArray(json.people_searches)) {
      throw new Error(t("errors.loadFailed"));
    }
    setItems(json.people_searches);
  }

  async function create() {
    setPending(true);
    setError(null);
    try {
      const resp = await fetch("/api/people-searches", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          title,
          search_query: boolean.query || searchQuery,
          people_prompt_id: peoplePromptId || undefined,
          people_prompt: peoplePromptId ? undefined : peoplePrompt,
          linkedin_filters: linkedinFilters,
          status: "active",
        }),
      });
      const json = (await resp.json().catch(() => null)) as { ok?: boolean; error?: string } | null;
      if (!resp.ok || !json?.ok) throw new Error(json?.error || t("errors.saveFailed"));
      setTitle("");
      setSearchQuery("");
      setPeoplePromptId("");
      setPeoplePrompt(`${DEFAULT_PEOPLE_PROMPT}\n`);
      setLinkedinFilters(DEFAULT_PEOPLE_FILTERS);
      await refresh();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t("errors.saveFailed"));
    } finally {
      setPending(false);
    }
  }

  async function remove(id: string) {
    setPending(true);
    setError(null);
    try {
      const resp = await fetch(`/api/people-searches/${encodeURIComponent(id)}`, {
        method: "DELETE",
      });
      const json = (await resp.json().catch(() => null)) as { ok?: boolean; error?: string } | null;
      if (!resp.ok || !json?.ok) throw new Error(json?.error || t("errors.deleteFailed"));
      await refresh();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t("errors.deleteFailed"));
    } finally {
      setPending(false);
    }
  }

  const filterCount = peopleFiltersActiveCount(linkedinFilters);

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-border bg-card p-6">
        <div className="space-y-1">
          <h3 className="text-base font-semibold">{t("create.title")}</h3>
          <p className="text-sm text-muted-foreground">{t("create.description")}</p>
        </div>

        <div className="mt-5 grid gap-4">
          <div className="grid gap-2">
            <Label htmlFor="people_title">{t("fields.title")}</Label>
            <Input id="people_title" value={title} onChange={(e) => setTitle(e.target.value)} />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="people_query">{t("fields.searchQuery")}</Label>
            <Input
              id="people_query"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={t("fields.searchQueryPlaceholder")}
            />
            <BooleanHint query={searchQuery} />
          </div>
          <div>
            <Button type="button" variant="outline" className="h-9 rounded-full" onClick={() => setFiltersOpen(true)}>
              {t("fields.allFilters")}
              {filterCount ? ` · ${filterCount}` : ""}
            </Button>
          </div>
          <PromptPicker
            label={t("fields.peoplePrompt")}
            value={peoplePromptId}
            options={prompts}
            fallbackBody={peoplePrompt}
            emptyLabel={t("fields.promptEmpty")}
            editLabel={t("fields.editPrompt")}
            onChange={setPeoplePromptId}
          />
          {!peoplePromptId ? (
            <div className="grid gap-2">
              <Label htmlFor="people_prompt">{t("fields.peoplePrompt")}</Label>
              <Textarea
                id="people_prompt"
                value={peoplePrompt}
                onChange={(e) => setPeoplePrompt(e.target.value)}
                rows={8}
              />
              <p className="text-xs text-muted-foreground">
                {t("fields.markerHint", { marker: PEOPLE_REQUIRED_MARKER })}
              </p>
            </div>
          ) : null}

          {error ? <div className="text-sm text-destructive">{error}</div> : null}

          <Button type="button" onClick={create} disabled={pending || !canCreate} className="h-10 rounded-full">
            {pending ? t("create.pending") : t("create.submit")}
          </Button>
        </div>
      </div>

      <div className="space-y-3">
        <h3 className="text-base font-semibold">{t("list.title")}</h3>
        {items.length === 0 ? (
          <div className="rounded-2xl border border-border/80 bg-muted/40 px-6 py-5 text-sm text-muted-foreground">
            {t("list.empty")}
          </div>
        ) : null}
        {items.map((s) => (
          <PeopleSearchCard
            key={`${s.id}:${s.last_run_at ?? ""}:${s.status ?? ""}`}
            item={s}
            busy={pending}
            prompts={prompts}
            onSaved={refresh}
            onRemove={remove}
          />
        ))}
      </div>

      <AllFiltersDialog
        open={filtersOpen}
        value={linkedinFilters}
        onClose={() => setFiltersOpen(false)}
        onApply={setLinkedinFilters}
      />
    </div>
  );
}

function PeopleSearchCard({
  item,
  busy,
  prompts,
  onSaved,
  onRemove,
}: {
  item: PeopleSearchDto;
  busy: boolean;
  prompts: PromptOption[];
  onSaved: () => Promise<void>;
  onRemove: (id: string) => Promise<void>;
}) {
  const t = useTranslations("people.prompts");
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [title, setTitle] = useState(item.title);
  const [searchQuery, setSearchQuery] = useState(item.search_query);
  const [peoplePrompt, setPeoplePrompt] = useState(item.people_prompt);
  const [peoplePromptId, setPeoplePromptId] = useState(item.people_prompt_id || "");
  const [linkedinFilters, setLinkedinFilters] = useState<PeopleFilters>(
    normalizePeopleFilters(item.linkedin_filters),
  );
  const [filtersOpen, setFiltersOpen] = useState(false);
  const boolean = normalizeBooleanQuery(searchQuery);
  const matchCount = typeof item.new_match_count === "number" ? item.new_match_count : 0;
  const canSave =
    title.trim().length > 0 &&
    searchQuery.trim().length > 0 &&
    boolean.ok &&
    peoplePrompt.trim().length > 0 &&
    peoplePrompt.includes(PEOPLE_REQUIRED_MARKER);

  async function save() {
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      const resp = await fetch(`/api/people-searches/${encodeURIComponent(item.id)}`, {
        method: "PATCH",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          title,
          search_query: boolean.query || searchQuery,
          people_prompt: peoplePrompt,
          people_prompt_id: peoplePromptId || undefined,
          linkedin_filters: linkedinFilters,
        }),
      });
      const json = (await resp.json().catch(() => null)) as { ok?: boolean; error?: string } | null;
      if (!resp.ok || !json?.ok) throw new Error(json?.error || t("errors.saveFailed"));
      await onSaved();
      setSaved(true);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t("errors.saveFailed"));
    } finally {
      setSaving(false);
    }
  }

  const filterCount = peopleFiltersActiveCount(linkedinFilters);

  return (
    <div className="rounded-2xl border border-border bg-card p-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-1">
          <div className="text-base font-semibold">{item.title}</div>
          <div className="text-sm text-muted-foreground">
            {item.status === "paused" ? t("status.paused") : t("status.active")}
            {matchCount ? ` · ${t("list.newMatches", { count: matchCount })}` : ""}
            {typeof item.target_found_count === "number"
              ? ` · ${t("list.targetFound", { count: item.target_found_count })}`
              : ""}
          </div>
          <SearchTariffSummary tariff={item.search_tariff ?? null} kind="people" className="text-sm" />
        </div>
        <PeopleSearchRunButton peopleSearchId={item.id} disabled={busy || saving} onDone={onSaved} />
      </div>

      {!open ? (
        <button
          type="button"
          className={cn(
            buttonVariants({ variant: "outline", size: "sm" }),
            "mt-4 h-9 rounded-full px-4 text-muted-foreground hover:text-foreground",
          )}
          onClick={() => setOpen(true)}
        >
          <ChevronDown className="size-4" />
          {t("edit.toggle")}
        </button>
      ) : (
        <div className="mt-4 grid gap-4">
          <div className="grid gap-2">
            <Label>{t("fields.title")}</Label>
            <Input value={title} onChange={(e) => setTitle(e.target.value)} disabled={busy || saving} />
          </div>
          <div className="grid gap-2">
            <Label>{t("fields.searchQuery")}</Label>
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              disabled={busy || saving}
            />
            <BooleanHint query={searchQuery} />
          </div>
          <div>
            <Button
              type="button"
              variant="outline"
              className="h-9 rounded-full"
              onClick={() => setFiltersOpen(true)}
              disabled={busy || saving}
            >
              {t("fields.allFilters")}
              {filterCount ? ` · ${filterCount}` : ""}
            </Button>
          </div>
          <PromptPicker
            label={t("fields.peoplePrompt")}
            value={peoplePromptId}
            options={prompts}
            fallbackBody={peoplePrompt}
            emptyLabel={t("fields.promptEmpty")}
            editLabel={t("fields.editPrompt")}
            onChange={(id) => {
              setPeoplePromptId(id);
              const found = prompts.find((p) => p.id === id);
              if (found?.body) setPeoplePrompt(found.body);
            }}
          />
          <div className="grid gap-2">
            <Label>{t("fields.peoplePrompt")}</Label>
            <Textarea
              value={peoplePrompt}
              rows={8}
              onChange={(e) => setPeoplePrompt(e.target.value)}
              disabled={busy || saving}
            />
            <p className="text-xs text-muted-foreground">{t("fields.markerHint", { marker: PEOPLE_REQUIRED_MARKER })}</p>
          </div>

          {error ? <div className="text-sm text-destructive">{error}</div> : null}
          {saved ? <div className="text-sm text-emerald-600 dark:text-emerald-300">{t("edit.saved")}</div> : null}

          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              variant="outline"
              className="h-9 rounded-full px-4 text-muted-foreground hover:text-foreground"
              onClick={() => setOpen(false)}
              disabled={saving}
            >
              <ChevronUp className="size-4" />
              {t("edit.collapse")}
            </Button>
            <Button type="button" className="h-9 rounded-full" onClick={save} disabled={busy || saving || !canSave}>
              {saving ? t("edit.saving") : t("edit.save")}
            </Button>
            <Button
              type="button"
              variant="destructive"
              className="h-9 rounded-full"
              onClick={() => {
                if (!window.confirm(t("edit.deleteConfirm"))) return;
                void onRemove(item.id);
              }}
              disabled={busy || saving}
            >
              {t("edit.delete")}
            </Button>
          </div>
        </div>
      )}

      <AllFiltersDialog
        open={filtersOpen}
        value={linkedinFilters}
        onClose={() => setFiltersOpen(false)}
        onApply={setLinkedinFilters}
      />
    </div>
  );
}
