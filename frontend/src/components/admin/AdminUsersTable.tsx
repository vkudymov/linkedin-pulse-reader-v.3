"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Briefcase, ChevronDown, MessageSquareText, Play, RefreshCw, Save, Shield, UserX } from "lucide-react";
import { useTranslations } from "next-intl";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

type AdminUserRow = {
  id: string;
  email: string | null;
  created_at: string | null;
  full_name: string | null;
  is_admin: boolean;
  is_blocked: boolean;
  blocked_at: string | null;
  post_search_run_count: number;
};

type UserProfileDetails = {
  id: string;
  full_name: string | null;
  phone: string | null;
  avatar_url: string | null;
  company: string | null;
  job_title: string | null;
  date_of_birth: string | null;
  city: string | null;
  bio: string | null;
  website: string | null;
  created_at: string | null;
  updated_at: string | null;
};

type UserPromptsDetails = {
  id: string;
  search_prompt: string | null;
  comment_prompt: string | null;
  created_at: string | null;
  updated_at: string | null;
};

type AdminJobSearchDto = {
  id: string;
  user_id: string;
  title: string;
  search_query: string;
  location: string | null;
  filter_prompt: string;
  status: string | null;
  last_run_at: string | null;
  created_at: string | null;
  updated_at: string | null;
};

const fieldClassName =
  "h-11 rounded-full border-border/80 bg-secondary px-4 text-sm text-foreground shadow-none";

function initialsFromName(name: string | null | undefined) {
  const raw = (name || "").trim();
  if (!raw) return "?";
  const parts = raw.split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

async function postJson(path: string) {
  const resp = await fetch(path, { method: "POST" });
  const text = await resp.text();
  if (!resp.ok) {
    throw new Error(text || "request failed");
  }
  return text;
}

export function AdminUsersTable({
  initialUsers,
  loadError = null,
}: {
  initialUsers: AdminUserRow[];
  loadError?: string | null;
}) {
  const router = useRouter();
  const t = useTranslations("adminUsers");
  const tProfile = useTranslations("profileForm");
  const tPostSearch = useTranslations("postSearch");
  const tJobRunner = useTranslations("jobs.runner");
  const JOB_MARKER = "<<<JOB_TEXT>>>";
  const POST_MARKER = "<<<POST_TEXT>>>";
  const POST_COMMENT_REQUIRED_MARKERS = [
    "<<<POST_TEXT>>>",
    "<<<CONTENT_TYPE>>>",
    "<<<MAIN_TOPICS>>>",
    "<<<TARGET_LANGUAGE>>>",
  ];
  const [pendingId, setPendingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [openDetailsById, setOpenDetailsById] = useState<Record<string, boolean>>({});
  const [openPromptsById, setOpenPromptsById] = useState<Record<string, boolean>>({});
  const [detailsById, setDetailsById] = useState<Record<string, UserProfileDetails | null>>({});
  const [detailsErrorById, setDetailsErrorById] = useState<Record<string, string | null>>({});
  const [savePendingById, setSavePendingById] = useState<Record<string, boolean>>({});
  const [saveErrorById, setSaveErrorById] = useState<Record<string, string | null>>({});
  const [saveSuccessById, setSaveSuccessById] = useState<Record<string, string | null>>({});
  const [promptsById, setPromptsById] = useState<Record<string, UserPromptsDetails | null>>({});
  const [promptsErrorById, setPromptsErrorById] = useState<Record<string, string | null>>({});
  const [savePromptsErrorById, setSavePromptsErrorById] = useState<Record<string, string | null>>(
    {},
  );
  const [savePromptsSuccessById, setSavePromptsSuccessById] = useState<
    Record<string, string | null>
  >({});
  const [postSearchPromptDraftByUserId, setPostSearchPromptDraftByUserId] = useState<Record<string, string>>({});
  const [postCommentPromptDraftByUserId, setPostCommentPromptDraftByUserId] = useState<Record<string, string>>({});
  const [postPromptsOpenByUserId, setPostPromptsOpenByUserId] = useState<Record<string, boolean>>({});
  const [savePostPromptsPendingByUserId, setSavePostPromptsPendingByUserId] = useState<Record<string, boolean>>({});
  const [postRunPendingByUserId, setPostRunPendingByUserId] = useState<Record<string, boolean>>({});
  const [postRunStatusByUserId, setPostRunStatusByUserId] = useState<Record<string, string | null>>({});
  const [postRunMessageByUserId, setPostRunMessageByUserId] = useState<Record<string, string | null>>({});
  const [postRunErrorByUserId, setPostRunErrorByUserId] = useState<Record<string, string | null>>({});

  const [jobSearchesByUserId, setJobSearchesByUserId] = useState<
    Record<string, AdminJobSearchDto[] | null>
  >({});
  const [jobSearchesErrorByUserId, setJobSearchesErrorByUserId] = useState<Record<string, string | null>>(
    {},
  );
  const [jobSearchDraftByKey, setJobSearchDraftByKey] = useState<Record<string, string>>({});
  const [jobSearchOpenByKey, setJobSearchOpenByKey] = useState<Record<string, boolean>>({});
  const [saveJobSearchPendingByKey, setSaveJobSearchPendingByKey] = useState<Record<string, boolean>>({});
  const [saveJobSearchErrorByKey, setSaveJobSearchErrorByKey] = useState<Record<string, string | null>>({});
  const [saveJobSearchSuccessByKey, setSaveJobSearchSuccessByKey] = useState<Record<string, string | null>>(
    {},
  );
  const [jobRunPendingByKey, setJobRunPendingByKey] = useState<Record<string, boolean>>({});
  const [jobRunStatusByKey, setJobRunStatusByKey] = useState<Record<string, string | null>>({});
  const [jobRunMessageByKey, setJobRunMessageByKey] = useState<Record<string, string | null>>({});
  const [jobRunErrorByKey, setJobRunErrorByKey] = useState<Record<string, string | null>>({});

  const users = useMemo(() => initialUsers || [], [initialUsers]);

  async function ensureDetails(userId: string) {
    if (detailsById[userId] !== undefined) return;
    setDetailsErrorById((m) => ({ ...m, [userId]: null }));
    try {
      const resp = await fetch(`/api/admin/users/${encodeURIComponent(userId)}/profile`, {
        method: "GET",
      });
      if (!resp.ok) {
        const text = await resp.text().catch(() => "");
        throw new Error(text || t("errors.loadProfile"));
      }
      const json = (await resp.json()) as UserProfileDetails;
      setDetailsById((m) => ({ ...m, [userId]: json }));
    } catch (e: unknown) {
      setDetailsById((m) => ({ ...m, [userId]: null }));
      setDetailsErrorById((m) => ({
        ...m,
        [userId]: e instanceof Error ? e.message : t("errors.loadProfile"),
      }));
    }
  }

  async function ensurePrompts(userId: string) {
    if (promptsById[userId] !== undefined) return;
    setPromptsErrorById((m) => ({ ...m, [userId]: null }));
    try {
      const resp = await fetch(`/api/admin/users/${encodeURIComponent(userId)}/prompts`, {
        method: "GET",
      });
      if (!resp.ok) {
        const text = await resp.text().catch(() => "");
        throw new Error(text || t("errors.loadPrompts"));
      }
      const json = (await resp.json()) as UserPromptsDetails;
      setPromptsById((m) => ({ ...m, [userId]: json }));
      setPostSearchPromptDraftByUserId((m) =>
        m[userId] === undefined ? { ...m, [userId]: json.search_prompt || "" } : m,
      );
      setPostCommentPromptDraftByUserId((m) =>
        m[userId] === undefined ? { ...m, [userId]: json.comment_prompt || "" } : m,
      );
    } catch (e: unknown) {
      setPromptsById((m) => ({ ...m, [userId]: null }));
      setPromptsErrorById((m) => ({
        ...m,
        [userId]: e instanceof Error ? e.message : t("errors.loadPrompts"),
      }));
    }
  }

  async function refreshPrompts(userId: string) {
    setPromptsErrorById((m) => ({ ...m, [userId]: null }));
    try {
      const resp = await fetch(`/api/admin/users/${encodeURIComponent(userId)}/prompts`, {
        method: "GET",
        cache: "no-store",
      });
      if (!resp.ok) {
        const text = await resp.text().catch(() => "");
        throw new Error(text || t("errors.loadPrompts"));
      }
      const json = (await resp.json()) as UserPromptsDetails;
      setPromptsById((m) => ({ ...m, [userId]: json }));
      setPostSearchPromptDraftByUserId((m) => ({ ...m, [userId]: json.search_prompt || "" }));
      setPostCommentPromptDraftByUserId((m) => ({ ...m, [userId]: json.comment_prompt || "" }));
    } catch (e: unknown) {
      setPromptsById((m) => ({ ...m, [userId]: null }));
      setPromptsErrorById((m) => ({
        ...m,
        [userId]: e instanceof Error ? e.message : t("errors.loadPrompts"),
      }));
    }
  }

  function missingMarkers(value: string, markers: string[]) {
    return markers.filter((m) => !value.includes(m));
  }

  async function onSavePostPrompts(userId: string) {
    const search_prompt = (postSearchPromptDraftByUserId[userId] ?? "").trim();
    const rawComment = postCommentPromptDraftByUserId[userId] ?? "";
    const comment_prompt = rawComment.trim() || null;

    setSavePromptsErrorById((m) => ({ ...m, [userId]: null }));
    setSavePromptsSuccessById((m) => ({ ...m, [userId]: null }));
    setSavePostPromptsPendingByUserId((m) => ({ ...m, [userId]: true }));
    try {
      if (!search_prompt) throw new Error(t("posts.errors.emptySearch"));
      if (!search_prompt.includes(POST_MARKER)) {
        throw new Error(t("posts.errors.missingMarker", { marker: POST_MARKER }));
      }
      if (comment_prompt) {
        const missing = missingMarkers(comment_prompt, POST_COMMENT_REQUIRED_MARKERS);
        if (missing.length > 0) {
          throw new Error(t("posts.errors.missingCommentMarkers", { markers: missing.join(", ") }));
        }
      }

      const resp = await fetch(`/api/admin/users/${encodeURIComponent(userId)}/prompts`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ search_prompt, comment_prompt }),
      });
      const text = await resp.text().catch(() => "");
      if (!resp.ok) throw new Error(text || t("errors.savePrompts"));
      setSavePromptsSuccessById((m) => ({ ...m, [userId]: t("common.saved") }));
      void refreshPrompts(userId);
    } catch (e: unknown) {
      setSavePromptsErrorById((m) => ({
        ...m,
        [userId]: e instanceof Error ? e.message : t("errors.savePrompts"),
      }));
    } finally {
      setSavePostPromptsPendingByUserId((m) => ({ ...m, [userId]: false }));
    }
  }

  function jobKey(userId: string, jobSearchId: string) {
    return `${userId}:${jobSearchId}`;
  }

  async function sleep(ms: number) {
    await new Promise((r) => setTimeout(r, ms));
  }

  async function startPostSearch(userId: string) {
    setPostRunPendingByUserId((m) => ({ ...m, [userId]: true }));
    setPostRunErrorByUserId((m) => ({ ...m, [userId]: null }));
    setPostRunStatusByUserId((m) => ({ ...m, [userId]: null }));
    setPostRunMessageByUserId((m) => ({ ...m, [userId]: null }));
    try {
      const runResp = await fetch(`/api/admin/users/${encodeURIComponent(userId)}/post-search/run`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({}),
      });
      const runJson = (await runResp.json().catch(() => null)) as
        | { session_id?: string; status?: string; message?: string | null }
        | null;
      if (!runResp.ok || !runJson?.session_id) {
        throw new Error(runJson?.message || tPostSearch("errors.startFailed"));
      }

      setPostRunStatusByUserId((m) => ({ ...m, [userId]: runJson.status ?? "running" }));
      setPostRunMessageByUserId((m) => ({ ...m, [userId]: runJson.message ?? null }));

      for (let attempt = 0; attempt < 600; attempt += 1) {
        await sleep(1000);
        const stResp = await fetch(
          `/api/admin/users/${encodeURIComponent(userId)}/post-search/run/${encodeURIComponent(runJson.session_id)}`,
          { method: "GET", cache: "no-store" },
        );
        const stJson = (await stResp.json().catch(() => null)) as
          | { status?: string; message?: string | null }
          | null;
        if (!stResp.ok || !stJson) throw new Error(tPostSearch("errors.statusFailed"));
        setPostRunStatusByUserId((m) => ({ ...m, [userId]: stJson.status ?? null }));
        setPostRunMessageByUserId((m) => ({ ...m, [userId]: stJson.message ?? null }));
        if (stJson.status === "done") {
          void refreshPrompts(userId);
          router.refresh();
          return;
        }
        if (stJson.status === "error") {
          throw new Error(stJson.message || tPostSearch("errors.runFailed"));
        }
      }
      throw new Error(tPostSearch("errors.timeout"));
    } catch (e: unknown) {
      setPostRunErrorByUserId((m) => ({
        ...m,
        [userId]: e instanceof Error ? e.message : tPostSearch("errors.startFailed"),
      }));
    } finally {
      setPostRunPendingByUserId((m) => ({ ...m, [userId]: false }));
    }
  }

  async function startJobSearch(userId: string, jobSearchId: string) {
    const k = jobKey(userId, jobSearchId);
    setJobRunPendingByKey((m) => ({ ...m, [k]: true }));
    setJobRunErrorByKey((m) => ({ ...m, [k]: null }));
    setJobRunStatusByKey((m) => ({ ...m, [k]: null }));
    setJobRunMessageByKey((m) => ({ ...m, [k]: null }));
    try {
      const runResp = await fetch(`/api/admin/users/${encodeURIComponent(userId)}/job-search/run`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ job_search_id: jobSearchId, limit: 25 }),
      });
      const runJson = (await runResp.json().catch(() => null)) as
        | { session_id?: string; status?: string; message?: string | null }
        | null;
      if (!runResp.ok || !runJson?.session_id) {
        throw new Error(runJson?.message || tJobRunner("errors.startFailed"));
      }

      setJobRunStatusByKey((m) => ({ ...m, [k]: runJson.status ?? "running" }));
      setJobRunMessageByKey((m) => ({ ...m, [k]: runJson.message ?? null }));

      for (let attempt = 0; attempt < 600; attempt += 1) {
        await sleep(1000);
        const stResp = await fetch(
          `/api/admin/users/${encodeURIComponent(userId)}/job-search/run/${encodeURIComponent(runJson.session_id)}`,
          { method: "GET", cache: "no-store" },
        );
        const stJson = (await stResp.json().catch(() => null)) as
          | { status?: string; message?: string | null }
          | null;
        if (!stResp.ok || !stJson) throw new Error(tJobRunner("errors.statusFailed"));
        setJobRunStatusByKey((m) => ({ ...m, [k]: stJson.status ?? null }));
        setJobRunMessageByKey((m) => ({ ...m, [k]: stJson.message ?? null }));
        if (stJson.status === "done") {
          await refreshJobSearches(userId);
          return;
        }
        if (stJson.status === "error") {
          throw new Error(stJson.message || tJobRunner("errors.runFailed"));
        }
      }
      throw new Error(tJobRunner("errors.timeout"));
    } catch (e: unknown) {
      setJobRunErrorByKey((m) => ({
        ...m,
        [k]: e instanceof Error ? e.message : tJobRunner("errors.startFailed"),
      }));
    } finally {
      setJobRunPendingByKey((m) => ({ ...m, [k]: false }));
    }
  }

  async function ensureJobSearches(userId: string) {
    if (jobSearchesByUserId[userId] !== undefined) return;
    setJobSearchesErrorByUserId((m) => ({ ...m, [userId]: null }));
    try {
      const resp = await fetch(`/api/admin/users/${encodeURIComponent(userId)}/job-searches`, {
        method: "GET",
        cache: "no-store",
      });
      if (!resp.ok) {
        const text = await resp.text().catch(() => "");
        throw new Error(text || t("jobs.errors.load"));
      }
      const json = (await resp.json()) as AdminJobSearchDto[];
      setJobSearchesByUserId((m) => ({ ...m, [userId]: json }));
      setJobSearchDraftByKey((m) => {
        const next = { ...m };
        for (const row of json) {
          if (!row?.id) continue;
          const k = jobKey(userId, row.id);
          if (next[k] === undefined) next[k] = row.filter_prompt || "";
        }
        return next;
      });
    } catch (e: unknown) {
      setJobSearchesByUserId((m) => ({ ...m, [userId]: null }));
      setJobSearchesErrorByUserId((m) => ({
        ...m,
        [userId]: e instanceof Error ? e.message : t("jobs.errors.load"),
      }));
    }
  }

  async function refreshJobSearches(userId: string) {
    setJobSearchesErrorByUserId((m) => ({ ...m, [userId]: null }));
    try {
      const resp = await fetch(`/api/admin/users/${encodeURIComponent(userId)}/job-searches`, {
        method: "GET",
        cache: "no-store",
      });
      if (!resp.ok) {
        const text = await resp.text().catch(() => "");
        throw new Error(text || t("jobs.errors.load"));
      }
      const json = (await resp.json()) as AdminJobSearchDto[];
      setJobSearchesByUserId((m) => ({ ...m, [userId]: json }));
    } catch (e: unknown) {
      setJobSearchesByUserId((m) => ({ ...m, [userId]: null }));
      setJobSearchesErrorByUserId((m) => ({
        ...m,
        [userId]: e instanceof Error ? e.message : t("jobs.errors.load"),
      }));
    }
  }

  async function onSaveJobSearchPrompt(userId: string, jobSearchId: string) {
    const k = jobKey(userId, jobSearchId);
    const prompt = (jobSearchDraftByKey[k] ?? "").trim();
    setSaveJobSearchPendingByKey((m) => ({ ...m, [k]: true }));
    setSaveJobSearchErrorByKey((m) => ({ ...m, [k]: null }));
    setSaveJobSearchSuccessByKey((m) => ({ ...m, [k]: null }));
    try {
      if (!prompt) throw new Error(t("jobs.errors.emptyPrompt"));
      if (!prompt.includes(JOB_MARKER)) throw new Error(t("jobs.errors.missingMarker", { marker: JOB_MARKER }));
      const resp = await fetch(
        `/api/admin/users/${encodeURIComponent(userId)}/job-searches/${encodeURIComponent(jobSearchId)}`,
        {
          method: "PATCH",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ filter_prompt: prompt }),
        },
      );
      const text = await resp.text().catch(() => "");
      if (!resp.ok) throw new Error(text || t("jobs.errors.save"));
      setSaveJobSearchSuccessByKey((m) => ({ ...m, [k]: t("common.saved") }));
      await refreshJobSearches(userId);
    } catch (e: unknown) {
      setSaveJobSearchErrorByKey((m) => ({ ...m, [k]: e instanceof Error ? e.message : t("jobs.errors.save") }));
    } finally {
      setSaveJobSearchPendingByKey((m) => ({ ...m, [k]: false }));
    }
  }

  async function onSaveDetails(userId: string) {
    const details = detailsById[userId];
    if (!details) return;
    setSavePendingById((m) => ({ ...m, [userId]: true }));
    setSaveErrorById((m) => ({ ...m, [userId]: null }));
    setSaveSuccessById((m) => ({ ...m, [userId]: null }));
    try {
      const payload = {
        full_name: details.full_name || null,
        phone: details.phone || null,
        avatar_url: details.avatar_url || null,
        company: details.company || null,
        job_title: details.job_title || null,
        date_of_birth: details.date_of_birth || null,
        city: details.city || null,
        bio: details.bio || null,
        website: details.website || null,
      };
      const resp = await fetch(`/api/admin/users/${encodeURIComponent(userId)}/profile`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(payload),
      });
      const text = await resp.text().catch(() => "");
      if (!resp.ok) throw new Error(text || t("errors.saveProfile"));
      setSaveSuccessById((m) => ({ ...m, [userId]: t("common.saved") }));
      router.refresh();
    } catch (e: unknown) {
      setSaveErrorById((m) => ({
        ...m,
        [userId]: e instanceof Error ? e.message : t("errors.saveProfile"),
      }));
    } finally {
      setSavePendingById((m) => ({ ...m, [userId]: false }));
    }
  }

  async function onBlock(userId: string) {
    setPendingId(userId);
    setError(null);
    try {
      await postJson(`/api/admin/users/${encodeURIComponent(userId)}/block`);
      router.refresh();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t("errors.request"));
    } finally {
      setPendingId(null);
    }
  }

  async function onUnblock(userId: string) {
    setPendingId(userId);
    setError(null);
    try {
      await postJson(`/api/admin/users/${encodeURIComponent(userId)}/unblock`);
      router.refresh();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t("errors.request"));
    } finally {
      setPendingId(null);
    }
  }

  async function onResetCount(userId: string) {
    setPendingId(userId);
    setError(null);
    try {
      await postJson(`/api/admin/users/${encodeURIComponent(userId)}/reset-post-search-count`);
      router.refresh();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t("errors.request"));
    } finally {
      setPendingId(null);
    }
  }

  return (
    <Card className="overflow-hidden rounded-2xl border border-border bg-card">
      <CardHeader className="border-b border-border px-6 py-5">
        <CardTitle className="text-lg font-semibold tracking-tight">{t("title")}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 p-6">
        {loadError ? (
          <div className="rounded-xl border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
            {t("errors.loadUsers")}
          </div>
        ) : null}
        {error ? (
          <div className="rounded-xl border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
            {error}
          </div>
        ) : null}

        <div className="space-y-3">
          {users.map((u) => {
            const pending = pendingId === u.id;
            const openDetails = Boolean(openDetailsById[u.id]);
            const openPrompts = Boolean(openPromptsById[u.id]);
            const email = u.email || "";
            const statusLabel = u.is_blocked ? t("status.blocked") : t("status.active");
            const displayName = u.full_name || "—";
            const details = detailsById[u.id];
            const prompts = promptsById[u.id] ?? null;
            const jobSearches = jobSearchesByUserId[u.id] ?? null;
            const avatarAlt = (displayName || email || tProfile("avatarAltFallback")).trim();
            const avatarFallback = initialsFromName(displayName || email);

            return (
              <Card key={u.id} className="overflow-hidden rounded-2xl border border-border bg-background/40">
                <CardHeader className="gap-2 px-6 pb-4 pt-5">
                    <div className="flex flex-wrap items-start justify-between gap-4">
                      <div className="min-w-0 space-y-1">
                        <div className="flex flex-wrap items-center gap-2">
                          {u.is_admin ? <Shield className="size-4 text-foreground/70" aria-hidden /> : null}
                          <div className="truncate text-base font-semibold tracking-tight">{displayName}</div>
                          <div className="truncate text-sm text-muted-foreground">{email}</div>
                          {u.is_admin ? (
                            <Badge variant="secondary" className="rounded-full">
                              admin
                            </Badge>
                          ) : null}
                        </div>
                      </div>

                      <span
                        className={cn(
                          "inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs",
                          u.is_blocked
                            ? "border-destructive/30 bg-destructive/10 text-destructive"
                            : "border-emerald-300/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
                        )}
                      >
                        {u.is_blocked ? <UserX className="size-3.5" aria-hidden /> : null}
                        {statusLabel}
                      </span>
                    </div>

                    <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
                      <div className="text-sm text-muted-foreground">
                        {t("postRuns.label")}{" "}
                        <span className="font-medium text-foreground">{u.post_search_run_count ?? 0}</span>
                      </div>

                      <div className="flex flex-wrap items-center justify-end gap-2">
                        <button
                          type="button"
                          className={cn(
                            buttonVariants({ variant: "outline", size: "sm" }),
                            "h-9 rounded-full px-4 text-muted-foreground hover:text-foreground",
                          )}
                          onClick={() => {
                            const next = !openDetails;
                            setOpenDetailsById((m) => ({ ...m, [u.id]: next }));
                            if (next) void ensureDetails(u.id);
                          }}
                        >
                          <ChevronDown className={cn("size-4 transition-transform", openDetails && "rotate-180")} />
                          {openDetails ? t("actions.collapse") : t("actions.details")}
                        </button>

                        <button
                          type="button"
                          className={cn(
                            buttonVariants({ variant: "outline", size: "sm" }),
                            "h-9 rounded-full px-4 text-muted-foreground hover:text-foreground",
                          )}
                          onClick={() => {
                            const next = !openPrompts;
                            setOpenPromptsById((m) => ({ ...m, [u.id]: next }));
                            if (next) {
                              void ensurePrompts(u.id);
                              void ensureJobSearches(u.id);
                            }
                          }}
                        >
                          <MessageSquareText className="size-4" aria-hidden />
                          {openPrompts ? t("actions.collapse") : t("actions.prompts")}
                        </button>

                        {u.is_blocked ? (
                          <Button
                            variant="outline"
                            size="sm"
                            disabled={pending}
                            className="h-9 rounded-full px-4"
                            onClick={() => onUnblock(u.id)}
                          >
                            {t("actions.unblock")}
                          </Button>
                        ) : (
                          <Button
                            variant="outline"
                            size="sm"
                            disabled={pending}
                            className="h-9 rounded-full px-4 text-destructive hover:text-destructive"
                            onClick={() => onBlock(u.id)}
                          >
                            {t("actions.block")}
                          </Button>
                        )}

                        <Button
                          variant="outline"
                          size="sm"
                          disabled={pending}
                          className="h-9 rounded-full px-4"
                          onClick={() => onResetCount(u.id)}
                        >
                          {t("actions.resetCount")}
                        </Button>
                      </div>
                    </div>
                  </CardHeader>

                  {openDetails ? (
                    <CardContent className="space-y-3 px-6 pb-6 pt-0">
                      {saveErrorById[u.id] ? (
                        <div className="rounded-xl border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                          {saveErrorById[u.id]}
                        </div>
                      ) : null}
                      {saveSuccessById[u.id] ? (
                        <div className="rounded-xl border border-emerald-300/40 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-700 dark:text-emerald-300">
                          {saveSuccessById[u.id]}
                        </div>
                      ) : null}

                      {detailsErrorById[u.id] ? (
                        <div className="rounded-xl border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                          {detailsErrorById[u.id]}
                        </div>
                      ) : null}

                      {detailsById[u.id] ? (
                        <form
                          className="space-y-6 rounded-xl border border-border bg-background/60 p-4"
                          onSubmit={(e) => {
                            e.preventDefault();
                            void onSaveDetails(u.id);
                          }}
                        >
                          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                            <div className="flex items-center gap-4">
                              <Avatar size="default" className="size-14">
                                {details?.avatar_url ? (
                                  <AvatarImage src={details.avatar_url} alt={avatarAlt} />
                                ) : null}
                                <AvatarFallback className="bg-background text-base font-medium text-foreground">
                                  {avatarFallback}
                                </AvatarFallback>
                              </Avatar>

                              <div className="min-w-0">
                                <div className="text-sm font-medium text-foreground">{t("profile.title")}</div>
                                <div className="text-sm text-muted-foreground">
                                  {t("profile.description")}
                                </div>
                              </div>
                            </div>
                          </div>

                          <div className="grid gap-5 sm:grid-cols-2">
                            <div className="space-y-2">
                              <Label htmlFor={`phone_${u.id}`}>{tProfile("fields.phone.label")}</Label>
                              <Input
                                id={`phone_${u.id}`}
                                className={fieldClassName}
                                autoComplete="tel"
                                value={details?.phone || ""}
                                onChange={(e) =>
                                  setDetailsById((m) => ({
                                    ...m,
                                    [u.id]: { ...(m[u.id] as UserProfileDetails), phone: e.target.value },
                                  }))
                                }
                                disabled={Boolean(savePendingById[u.id])}
                                placeholder="+7 999 000-00-00"
                              />
                            </div>

                            <div className="space-y-2">
                              <Label htmlFor={`company_${u.id}`}>{tProfile("fields.company.label")}</Label>
                              <Input
                                id={`company_${u.id}`}
                                className={fieldClassName}
                                value={details?.company || ""}
                                onChange={(e) =>
                                  setDetailsById((m) => ({
                                    ...m,
                                    [u.id]: { ...(m[u.id] as UserProfileDetails), company: e.target.value },
                                  }))
                                }
                                disabled={Boolean(savePendingById[u.id])}
                                placeholder={tProfile("fields.company.placeholder")}
                              />
                            </div>

                            <div className="space-y-2">
                              <Label htmlFor={`job_title_${u.id}`}>{tProfile("fields.jobTitle.label")}</Label>
                              <Input
                                id={`job_title_${u.id}`}
                                className={fieldClassName}
                                value={details?.job_title || ""}
                                onChange={(e) =>
                                  setDetailsById((m) => ({
                                    ...m,
                                    [u.id]: { ...(m[u.id] as UserProfileDetails), job_title: e.target.value },
                                  }))
                                }
                                disabled={Boolean(savePendingById[u.id])}
                                placeholder={tProfile("fields.jobTitle.placeholder")}
                              />
                            </div>

                            <div className="space-y-2">
                              <Label htmlFor={`date_of_birth_${u.id}`}>{tProfile("fields.dob.label")}</Label>
                              <Input
                                id={`date_of_birth_${u.id}`}
                                className={fieldClassName}
                                type="date"
                                value={details?.date_of_birth || ""}
                                onChange={(e) =>
                                  setDetailsById((m) => ({
                                    ...m,
                                    [u.id]: {
                                      ...(m[u.id] as UserProfileDetails),
                                      date_of_birth: e.target.value,
                                    },
                                  }))
                                }
                                disabled={Boolean(savePendingById[u.id])}
                              />
                            </div>

                            <div className="space-y-2">
                              <Label htmlFor={`city_${u.id}`}>{tProfile("fields.city.label")}</Label>
                              <Input
                                id={`city_${u.id}`}
                                className={fieldClassName}
                                value={details?.city || ""}
                                onChange={(e) =>
                                  setDetailsById((m) => ({
                                    ...m,
                                    [u.id]: { ...(m[u.id] as UserProfileDetails), city: e.target.value },
                                  }))
                                }
                                disabled={Boolean(savePendingById[u.id])}
                                placeholder={tProfile("fields.city.placeholder")}
                              />
                            </div>

                            <div className="space-y-2">
                              <Label htmlFor={`website_${u.id}`}>{tProfile("fields.website.label")}</Label>
                              <Input
                                id={`website_${u.id}`}
                                className={fieldClassName}
                                value={details?.website || ""}
                                onChange={(e) =>
                                  setDetailsById((m) => ({
                                    ...m,
                                    [u.id]: { ...(m[u.id] as UserProfileDetails), website: e.target.value },
                                  }))
                                }
                                disabled={Boolean(savePendingById[u.id])}
                                placeholder="https://example.com"
                              />
                            </div>
                          </div>

                          <div className="space-y-2">
                            <Label htmlFor={`avatar_url_${u.id}`}>Avatar URL</Label>
                            <Input
                              id={`avatar_url_${u.id}`}
                              className={fieldClassName}
                              value={details?.avatar_url || ""}
                              onChange={(e) =>
                                setDetailsById((m) => ({
                                  ...m,
                                  [u.id]: {
                                    ...(m[u.id] as UserProfileDetails),
                                    avatar_url: e.target.value,
                                  },
                                }))
                              }
                              disabled={Boolean(savePendingById[u.id])}
                              placeholder="https://..."
                            />
                          </div>

                          <div className="space-y-2">
                            <Label htmlFor={`bio_${u.id}`}>{tProfile("fields.bio.label")}</Label>
                            <Textarea
                              id={`bio_${u.id}`}
                              value={details?.bio || ""}
                              onChange={(e) =>
                                setDetailsById((m) => ({
                                  ...m,
                                  [u.id]: { ...(m[u.id] as UserProfileDetails), bio: e.target.value },
                                }))
                              }
                              disabled={Boolean(savePendingById[u.id])}
                              placeholder={t("profile.bioPlaceholder")}
                              className={cn("min-h-28 resize-y rounded-xl")}
                            />
                          </div>

                          <Button
                            type="submit"
                            className="h-11 w-full rounded-full bg-gradient-to-b from-neutral-200 to-neutral-400 text-sm font-semibold text-neutral-900 shadow-none hover:from-neutral-100 hover:to-neutral-300"
                            disabled={Boolean(savePendingById[u.id])}
                          >
                            <Save className="mr-2 size-4" />
                            {savePendingById[u.id] ? t("actions.saving") : t("actions.save")}
                          </Button>
                        </form>
                      ) : (
                        <div className="text-sm text-muted-foreground">{t("loading.profile")}</div>
                      )}
                    </CardContent>
                  ) : null}

                  {openPrompts ? (
                    <CardContent className="space-y-3 border-t border-border px-6 pb-6 pt-6">
                      {promptsErrorById[u.id] ? (
                        <div className="rounded-xl border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                          {promptsErrorById[u.id]}
                        </div>
                      ) : null}
                      {savePromptsErrorById[u.id] ? (
                        <div className="rounded-xl border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                          {savePromptsErrorById[u.id]}
                        </div>
                      ) : null}
                      {savePromptsSuccessById[u.id] ? (
                        <div className="rounded-xl border border-emerald-300/40 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-700 dark:text-emerald-300">
                          {savePromptsSuccessById[u.id]}
                        </div>
                      ) : null}

                      <div className="space-y-6 rounded-xl border border-border bg-background/60 p-4">
                        <div className="text-sm font-semibold">{t("sections.posts")}</div>
                        {prompts ? (
                          <div className="space-y-6">
                            <div className="rounded-2xl border border-border/80 bg-background/40 p-4">
                              <div className="flex flex-wrap items-start justify-between gap-3">
                                <div className="min-w-0">
                                  <div className="text-sm font-semibold">{t("posts.title")}</div>
                                  <div className="mt-1 text-xs text-muted-foreground">{t("posts.description")}</div>
                                </div>

                                <button
                                  type="button"
                                  className={cn(
                                    buttonVariants({ variant: "outline", size: "sm" }),
                                    "h-9 rounded-full px-4 text-muted-foreground hover:text-foreground",
                                  )}
                                  onClick={() =>
                                    setPostPromptsOpenByUserId((m) => ({ ...m, [u.id]: !Boolean(m[u.id]) }))
                                  }
                                >
                                  <ChevronDown
                                    className={cn(
                                      "size-4 transition-transform",
                                      Boolean(postPromptsOpenByUserId[u.id]) && "rotate-180",
                                    )}
                                  />
                                  {Boolean(postPromptsOpenByUserId[u.id])
                                    ? t("actions.collapse")
                                    : t("posts.actions.edit")}
                                </button>
                              </div>

                              {Boolean(postPromptsOpenByUserId[u.id]) ? (
                                <div className="mt-4 grid gap-4">
                                  <div className="grid gap-2">
                                    <Label htmlFor={`post_search_prompt_${u.id}`}>{t("posts.fields.searchPrompt")}</Label>
                                    <Textarea
                                      id={`post_search_prompt_${u.id}`}
                                      rows={8}
                                      value={postSearchPromptDraftByUserId[u.id] ?? prompts.search_prompt ?? ""}
                                      onChange={(e) =>
                                        setPostSearchPromptDraftByUserId((m) => ({ ...m, [u.id]: e.target.value }))
                                      }
                                    />
                                    <p className="text-xs text-muted-foreground">
                                      {t("posts.fields.markerHint", { marker: POST_MARKER })}
                                    </p>
                                  </div>

                                  <div className="grid gap-2">
                                    <Label htmlFor={`post_comment_prompt_${u.id}`}>{t("posts.fields.commentPrompt")}</Label>
                                    <Textarea
                                      id={`post_comment_prompt_${u.id}`}
                                      rows={8}
                                      value={postCommentPromptDraftByUserId[u.id] ?? prompts.comment_prompt ?? ""}
                                      onChange={(e) =>
                                        setPostCommentPromptDraftByUserId((m) => ({ ...m, [u.id]: e.target.value }))
                                      }
                                    />
                                    <p className="text-xs text-muted-foreground">{t("posts.fields.commentHint")}</p>
                                  </div>

                                  <div className="flex flex-wrap gap-2">
                                    <Button
                                      type="button"
                                      className="h-9 rounded-full"
                                      onClick={() => void onSavePostPrompts(u.id)}
                                      disabled={Boolean(savePostPromptsPendingByUserId[u.id])}
                                    >
                                      {savePostPromptsPendingByUserId[u.id] ? t("actions.saving") : t("actions.save")}
                                    </Button>

                                    <Button
                                      type="button"
                                      className="h-9 rounded-full"
                                      variant="outline"
                                      onClick={() => void startPostSearch(u.id)}
                                      disabled={Boolean(postRunPendingByUserId[u.id])}
                                    >
                                      {postRunPendingByUserId[u.id] ? (
                                        <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                                      ) : (
                                        <Play className="mr-2 h-4 w-4" />
                                      )}
                                      {postRunPendingByUserId[u.id]
                                        ? tPostSearch("button.pending")
                                        : tPostSearch("button.idle")}
                                    </Button>
                                  </div>

                                  {postRunStatusByUserId[u.id] || postRunMessageByUserId[u.id] ? (
                                    <div className="rounded-xl border border-border/80 bg-muted/40 px-4 py-3 text-sm text-muted-foreground">
                                      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                                        <span className="font-medium text-foreground">{tPostSearch("statusLabel")}</span>
                                        <span
                                          className={cn(postRunStatusByUserId[u.id] === "error" ? "text-destructive" : "")}
                                        >
                                          {postRunStatusByUserId[u.id] || "—"}
                                        </span>
                                      </div>
                                      {postRunMessageByUserId[u.id] ? (
                                        <div className="mt-1 whitespace-pre-wrap">{postRunMessageByUserId[u.id]}</div>
                                      ) : null}
                                    </div>
                                  ) : null}

                                  {postRunErrorByUserId[u.id] ? (
                                    <div className="rounded-xl border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
                                      {postRunErrorByUserId[u.id]}
                                    </div>
                                  ) : null}
                                </div>
                              ) : null}
                            </div>

                          </div>
                        ) : (
                          <div className="text-sm text-muted-foreground">{t("loading.prompts")}</div>
                        )}

                        <div className="border-t border-border/80 pt-6">
                          <div className="mb-3 flex items-center gap-2 text-sm font-semibold">
                            <Briefcase className="size-4 text-foreground/70" aria-hidden />
                            {t("sections.jobs")}
                          </div>

                          {jobSearchesErrorByUserId[u.id] ? (
                            <div className="rounded-xl border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                              {jobSearchesErrorByUserId[u.id]}
                            </div>
                          ) : null}

                          {jobSearches ? (
                            jobSearches.length === 0 ? (
                              <div className="rounded-xl border border-border/70 bg-muted/30 px-3 py-2 text-sm text-muted-foreground">
                                {t("jobs.empty")}
                              </div>
                            ) : (
                              <div className="space-y-3">
                                {jobSearches.map((s) => {
                                  const k = jobKey(u.id, s.id);
                                  const open = Boolean(jobSearchOpenByKey[k]);
                                  const draft = jobSearchDraftByKey[k] ?? s.filter_prompt ?? "";
                                  const saving = Boolean(saveJobSearchPendingByKey[k]);
                                  const canSave = draft.trim().length > 0 && draft.includes(JOB_MARKER);
                                  return (
                                    <div key={s.id} className="rounded-2xl border border-border/80 bg-background/40 p-4">
                                      <div className="flex flex-wrap items-start justify-between gap-3">
                                        <div className="min-w-0">
                                          <div className="text-sm font-semibold">{s.title}</div>
                                          <div className="mt-1 text-xs text-muted-foreground">
                                            <span className="font-medium text-foreground/90">{s.search_query}</span>
                                            {s.location ? ` · ${s.location}` : ""}
                                            {s.status ? ` · ${s.status}` : ""}
                                          </div>
                                        </div>

                                        <button
                                          type="button"
                                          className={cn(
                                            buttonVariants({ variant: "outline", size: "sm" }),
                                            "h-9 rounded-full px-4 text-muted-foreground hover:text-foreground",
                                          )}
                                          onClick={() => setJobSearchOpenByKey((m) => ({ ...m, [k]: !open }))}
                                        >
                                          <ChevronDown className={cn("size-4 transition-transform", open && "rotate-180")} />
                                          {open ? t("actions.collapse") : t("jobs.actions.edit")}
                                        </button>
                                      </div>

                                      {open ? (
                                        <div className="mt-4 grid gap-3">
                                          <div className="grid gap-2">
                                            <Label htmlFor={`job_prompt_${k}`}>{t("jobs.fields.filterPrompt")}</Label>
                                            <Textarea
                                              id={`job_prompt_${k}`}
                                              rows={8}
                                              value={draft}
                                              onChange={(e) =>
                                                setJobSearchDraftByKey((m) => ({ ...m, [k]: e.target.value }))
                                              }
                                              disabled={saving}
                                            />
                                            <p className="text-xs text-muted-foreground">
                                              {t("jobs.fields.markerHint", { marker: JOB_MARKER })}
                                            </p>
                                          </div>

                                          {saveJobSearchErrorByKey[k] ? (
                                            <div className="text-sm text-destructive">{saveJobSearchErrorByKey[k]}</div>
                                          ) : null}
                                          {saveJobSearchSuccessByKey[k] ? (
                                            <div className="text-sm text-emerald-600 dark:text-emerald-300">
                                              {saveJobSearchSuccessByKey[k]}
                                            </div>
                                          ) : null}

                                          <div className="flex flex-wrap items-center gap-2">
                                            <Button
                                              type="button"
                                              className="h-9 rounded-full"
                                              onClick={() => void onSaveJobSearchPrompt(u.id, s.id)}
                                              disabled={saving || !canSave}
                                            >
                                              {saving ? t("actions.saving") : t("actions.save")}
                                            </Button>

                                            <Button
                                              type="button"
                                              className="h-9 rounded-full"
                                              variant="outline"
                                              onClick={() => void startJobSearch(u.id, s.id)}
                                              disabled={Boolean(jobRunPendingByKey[k])}
                                            >
                                              {jobRunPendingByKey[k] ? (
                                                <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                                              ) : (
                                                <Play className="mr-2 h-4 w-4" />
                                              )}
                                              {jobRunPendingByKey[k] ? t("jobs.run.pending") : t("jobs.run.idle")}
                                            </Button>
                                          </div>

                                          {jobRunStatusByKey[k] || jobRunMessageByKey[k] ? (
                                            <div className="rounded-xl border border-border/80 bg-muted/40 px-4 py-3 text-sm text-muted-foreground">
                                              <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                                                <span className="font-medium text-foreground">{tJobRunner("statusLabel")}</span>
                                                <span className={cn(jobRunStatusByKey[k] === "error" ? "text-destructive" : "")}>
                                                  {jobRunStatusByKey[k] || "—"}
                                                </span>
                                              </div>
                                              {jobRunMessageByKey[k] ? (
                                                <div className="mt-1 whitespace-pre-wrap">{jobRunMessageByKey[k]}</div>
                                              ) : null}
                                            </div>
                                          ) : null}

                                          {jobRunErrorByKey[k] ? (
                                            <div className="text-sm text-destructive">{jobRunErrorByKey[k]}</div>
                                          ) : null}
                                        </div>
                                      ) : null}
                                    </div>
                                  );
                                })}
                              </div>
                            )
                          ) : (
                            <div className="text-sm text-muted-foreground">{t("jobs.loading")}</div>
                          )}
                        </div>
                      </div>
                    </CardContent>
                  ) : null}
              </Card>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}

