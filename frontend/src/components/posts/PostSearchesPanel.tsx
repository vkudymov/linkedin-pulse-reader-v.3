"use client";

import { useMemo, useState } from "react";
import { ChevronDown, ChevronUp, Play, RefreshCw } from "lucide-react";
import { useTranslations } from "next-intl";

import { Button, buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { SearchTariffSummary } from "@/components/SearchTariffSummary";
import type { SearchTariffInfo } from "@/lib/searchTariffs";

export type PostSearchDto = {
  id: string;
  title: string;
  search_prompt: string;
  comment_prompt: string | null;
  account_label: string | null;
  status: "active" | "paused" | string;
  last_run_at: string | null;
  email_report_enabled?: boolean;
  email_report_format?: string | null;
  target_found_count?: number;
  search_tariff_id?: string | null;
  search_tariff?: SearchTariffInfo | null;
  created_at?: string | null;
  updated_at?: string | null;
};

type RunResponse = {
  session_id: string;
  status: "running" | "done" | "error" | string;
  message?: string | null;
};

async function sleep(ms: number) {
  await new Promise((r) => setTimeout(r, ms));
}

const SEARCH_MARKER = "<<<POST_TEXT>>>";
const COMMENT_REQUIRED_MARKERS = ["<<<POST_TEXT>>>", "<<<CONTENT_TYPE>>>", "<<<MAIN_TOPICS>>>", "<<<TARGET_LANGUAGE>>>"];

function missingMarkers(value: string, markers: string[]): string[] {
  return markers.filter((m) => !value.includes(m));
}

export function PostSearchesPanel({ initial }: { initial: PostSearchDto[] }) {
  const t = useTranslations("posts.prompts");
  const [items, setItems] = useState<PostSearchDto[]>(initial);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [title, setTitle] = useState("");
  const [searchPrompt, setSearchPrompt] = useState(`${t("defaultSearchPrompt")}\n\n${SEARCH_MARKER}\n`);
  const [commentPrompt, setCommentPrompt] = useState("");
  const [accountLabel, setAccountLabel] = useState("");

  const canCreate = useMemo(() => {
    const sp = searchPrompt.trim();
    return title.trim().length > 0 && sp.length > 0 && sp.includes(SEARCH_MARKER);
  }, [title, searchPrompt]);

  async function refresh() {
    const resp = await fetch("/api/post-searches", { method: "GET", cache: "no-store" });
    const json = (await resp.json().catch(() => null)) as { ok?: boolean; post_searches?: PostSearchDto[]; error?: string } | null;
    if (!resp.ok || !json?.ok || !Array.isArray(json.post_searches)) {
      throw new Error(json?.error || t("errors.loadFailed"));
    }
    setItems(json.post_searches);
  }

  async function create() {
    setPending(true);
    setError(null);
    try {
      const sp = searchPrompt.trim();
      const cp = commentPrompt.trim();
      const missing = cp ? missingMarkers(cp, COMMENT_REQUIRED_MARKERS) : [];
      if (cp && missing.length > 0) throw new Error(t("errors.commentMissingMarkers", { markers: missing.join(", ") }));

      const resp = await fetch("/api/post-searches", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          title,
          search_prompt: sp,
          comment_prompt: cp || null,
          account_label: accountLabel.trim() || null,
          status: "active",
        }),
      });
      const json = (await resp.json().catch(() => null)) as { ok?: boolean; error?: string } | null;
      if (!resp.ok || !json?.ok) throw new Error(json?.error || t("errors.saveFailed"));
      setTitle("");
      setAccountLabel("");
      setCommentPrompt("");
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
      const resp = await fetch(`/api/post-searches/${encodeURIComponent(id)}`, { method: "DELETE" });
      const json = (await resp.json().catch(() => null)) as { ok?: boolean; error?: string } | null;
      if (!resp.ok || !json?.ok) throw new Error(json?.error || t("errors.deleteFailed"));
      await refresh();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t("errors.deleteFailed"));
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-border bg-card p-6">
        <div className="space-y-1">
          <h3 className="text-base font-semibold">{t("create.title")}</h3>
          <p className="text-sm text-muted-foreground">{t("create.description")}</p>
        </div>

        <div className="mt-5 grid gap-4">
          <div className="grid gap-2">
            <Label htmlFor="post_search_title">{t("fields.title")}</Label>
            <Input id="post_search_title" value={title} onChange={(e) => setTitle(e.target.value)} />
          </div>

          <div className="grid gap-2">
            <Label htmlFor="post_search_account_label">{t("fields.accountLabel")}</Label>
            <Input
              id="post_search_account_label"
              value={accountLabel}
              onChange={(e) => setAccountLabel(e.target.value)}
              placeholder={t("fields.accountLabelPlaceholder")}
            />
          </div>

          <div className="grid gap-2">
            <Label htmlFor="post_search_prompt">{t("fields.searchPrompt")}</Label>
            <Textarea id="post_search_prompt" value={searchPrompt} onChange={(e) => setSearchPrompt(e.target.value)} rows={8} />
            <p className="text-xs text-muted-foreground">{t("fields.searchMarkerHint", { marker: SEARCH_MARKER })}</p>
          </div>

          <div className="grid gap-2">
            <Label htmlFor="post_search_comment_prompt">{t("fields.commentPrompt")}</Label>
            <Textarea
              id="post_search_comment_prompt"
              value={commentPrompt}
              onChange={(e) => setCommentPrompt(e.target.value)}
              rows={6}
            />
            <p className="text-xs text-muted-foreground">{t("fields.commentMarkerHint")}</p>
          </div>

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
          <PostSearchCard
            key={`${s.id}:${s.updated_at ?? ""}:${s.last_run_at ?? ""}:${s.status ?? ""}`}
            item={s}
            busy={pending}
            onSaved={refresh}
            onRemove={remove}
          />
        ))}
      </div>
    </div>
  );
}

function PostSearchCard({
  item,
  busy,
  onSaved,
  onRemove,
}: {
  item: PostSearchDto;
  busy: boolean;
  onSaved: () => Promise<void>;
  onRemove: (id: string) => Promise<void>;
}) {
  const t = useTranslations("posts.prompts");
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [running, setRunning] = useState(false);
  const [runStatus, setRunStatus] = useState<string | null>(null);
  const [runMessage, setRunMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const [title, setTitle] = useState(item.title);
  const [accountLabel, setAccountLabel] = useState(item.account_label ?? "");
  const [searchPrompt, setSearchPrompt] = useState(item.search_prompt);
  const [commentPrompt, setCommentPrompt] = useState(item.comment_prompt ?? "");
  const [emailEnabled, setEmailEnabled] = useState(Boolean(item.email_report_enabled));
  const [emailFormat, setEmailFormat] = useState((item.email_report_format || "none").toString());

  const tariffAllowsEmailReports = item.search_tariff?.email_reports_enabled === true;

  const canSave = title.trim().length > 0 && searchPrompt.trim().length > 0 && searchPrompt.includes(SEARCH_MARKER);

  async function save() {
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      const sp = searchPrompt.trim();
      const cp = commentPrompt.trim();
      const missing = cp ? missingMarkers(cp, COMMENT_REQUIRED_MARKERS) : [];
      if (cp && missing.length > 0) throw new Error(t("errors.commentMissingMarkers", { markers: missing.join(", ") }));

      const resp = await fetch(`/api/post-searches/${encodeURIComponent(item.id)}`, {
        method: "PATCH",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          title,
          account_label: accountLabel.trim() || null,
          search_prompt: sp,
          comment_prompt: cp || null,
          email_report_enabled: tariffAllowsEmailReports ? emailEnabled : false,
          email_report_format: tariffAllowsEmailReports ? emailFormat : "none",
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

  async function run() {
    setRunning(true);
    setError(null);
    setRunStatus(null);
    setRunMessage(null);
    try {
      const runResp = await fetch("/api/post-search/run", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ post_search_id: item.id }),
      });
      const runJson = (await runResp.json().catch(() => null)) as RunResponse | null;
      if (!runResp.ok || !runJson?.session_id) throw new Error(runJson?.message || t("errors.runStartFailed"));
      setRunStatus(runJson.status);
      setRunMessage(runJson.message ?? null);

      for (let attempt = 0; attempt < 600; attempt += 1) {
        await sleep(1000);
        const stResp = await fetch(`/api/post-search/run/${encodeURIComponent(runJson.session_id)}`, { cache: "no-store" });
        const stJson = (await stResp.json().catch(() => null)) as RunResponse | null;
        if (!stResp.ok || !stJson) throw new Error(t("errors.runStatusFailed"));
        setRunStatus(stJson.status);
        setRunMessage(stJson.message ?? null);
        if (stJson.status === "done") {
          await onSaved();
          return;
        }
        if (stJson.status === "error") throw new Error(stJson.message || t("errors.runFailed"));
      }
      throw new Error(t("errors.runTimeout"));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t("errors.runFailed"));
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="rounded-2xl border border-border bg-card p-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-1">
          <div className="text-base font-semibold">{item.title}</div>
          <div className="text-sm text-muted-foreground">
            {item.status === "paused" ? t("status.paused") : t("status.active")}
            {typeof item.target_found_count === "number"
              ? ` · ${t("list.targetFound", { count: item.target_found_count })}`
              : ""}
          </div>
          <SearchTariffSummary tariff={item.search_tariff ?? null} className="text-sm" />
        </div>

        {!open ? (
          <button
            type="button"
            className={cn(
              buttonVariants({ variant: "outline", size: "sm" }),
              "h-9 rounded-full px-4 text-muted-foreground hover:text-foreground",
            )}
            onClick={() => setOpen(true)}
          >
            <ChevronDown className="size-4" />
            {t("edit.toggle")}
          </button>
        ) : null}
      </div>

      {open ? (
        <div className="mt-4 grid gap-4">
          <div className="grid gap-2">
            <Label>{t("fields.title")}</Label>
            <Input value={title} onChange={(e) => setTitle(e.target.value)} disabled={busy || saving || running} />
          </div>
          <div className="grid gap-2">
            <Label>{t("fields.accountLabel")}</Label>
            <Input
              value={accountLabel}
              onChange={(e) => setAccountLabel(e.target.value)}
              disabled={busy || saving || running}
              placeholder={t("fields.accountLabelPlaceholder")}
            />
          </div>
          <div className="grid gap-2">
            <Label>{t("fields.searchPrompt")}</Label>
            <Textarea value={searchPrompt} rows={8} onChange={(e) => setSearchPrompt(e.target.value)} disabled={busy || saving || running} />
            <p className="text-xs text-muted-foreground">{t("fields.searchMarkerHint", { marker: SEARCH_MARKER })}</p>
          </div>
          <div className="grid gap-2">
            <Label>{t("fields.commentPrompt")}</Label>
            <Textarea value={commentPrompt} rows={6} onChange={(e) => setCommentPrompt(e.target.value)} disabled={busy || saving || running} />
            <p className="text-xs text-muted-foreground">{t("fields.commentMarkerHint")}</p>
          </div>

          <div className="grid gap-2">
            <Label>{t("fields.emailReportFormat")}</Label>
            <select
              className="h-10 rounded-xl border border-border bg-background px-3 text-sm"
              value={tariffAllowsEmailReports ? emailFormat : "none"}
              disabled={busy || saving || running || !tariffAllowsEmailReports}
              onChange={(e) => setEmailFormat(e.target.value)}
            >
              <option value="none">{t("emailReport.formats.none")}</option>
              <option value="xlsx">{t("emailReport.formats.xlsx")}</option>
              <option value="docx">{t("emailReport.formats.docx")}</option>
              <option value="txt">{t("emailReport.formats.txt")}</option>
              <option value="json">{t("emailReport.formats.json")}</option>
              <option value="xml">{t("emailReport.formats.xml")}</option>
            </select>
            {!tariffAllowsEmailReports ? (
              <p className="text-xs text-muted-foreground">{t("emailReport.disabledByTariff")}</p>
            ) : null}
          </div>

          <div className="flex items-center gap-3">
            <input
              id={`email_enabled_${item.id}`}
              type="checkbox"
              checked={tariffAllowsEmailReports ? emailEnabled : false}
              disabled={busy || saving || running || !tariffAllowsEmailReports}
              onChange={(e) => setEmailEnabled(e.target.checked)}
            />
            <Label htmlFor={`email_enabled_${item.id}`}>{t("fields.emailReportEnabled")}</Label>
          </div>

          {runStatus || runMessage ? (
            <div className="rounded-xl border border-border/80 bg-muted/40 px-4 py-3 text-sm text-muted-foreground">
              <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                <span className="font-medium text-foreground">{t("run.statusLabel")}</span>
                <span className={cn(runStatus === "error" ? "text-destructive" : "")}>{runStatus || "—"}</span>
              </div>
              {runMessage ? <div className="mt-1 whitespace-pre-wrap">{runMessage}</div> : null}
            </div>
          ) : null}

          {error ? <div className="text-sm text-destructive">{error}</div> : null}
          {saved ? <div className="text-sm text-emerald-600 dark:text-emerald-300">{t("edit.saved")}</div> : null}

          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              variant="outline"
              className="h-9 rounded-full px-4 text-muted-foreground hover:text-foreground"
              onClick={() => setOpen(false)}
              disabled={saving || running}
            >
              <ChevronUp className="size-4" />
              {t("edit.collapse")}
            </Button>
            <Button type="button" className="h-9 rounded-full" onClick={save} disabled={busy || saving || running || !canSave}>
              {saving ? t("edit.saving") : t("edit.save")}
            </Button>
            <Button type="button" variant="outline" className="h-9 rounded-full" onClick={run} disabled={busy || saving || running}>
              {running ? <RefreshCw className="mr-2 h-4 w-4 animate-spin" /> : <Play className="mr-2 h-4 w-4" />}
              {running ? t("run.pending") : t("run.idle")}
            </Button>
            <Button
              type="button"
              variant="destructive"
              className="h-9 rounded-full"
              onClick={() => {
                if (!window.confirm(t("edit.deleteConfirm"))) return;
                void onRemove(item.id);
              }}
              disabled={busy || saving || running}
            >
              {t("edit.delete")}
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  );
}

