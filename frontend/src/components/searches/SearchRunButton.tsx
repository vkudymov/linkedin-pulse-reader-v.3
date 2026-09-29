"use client";

import { useState } from "react";
import { Play, RefreshCw } from "lucide-react";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type RunResponse = {
  session_id?: string;
  status?: string;
  message?: string | null;
};

async function sleep(ms: number) {
  await new Promise((r) => setTimeout(r, ms));
}

export function SearchRunButton({
  kind,
  searchId,
  userId,
  disabled,
  onDone,
}: {
  kind: "posts" | "jobs";
  searchId: string;
  userId?: string;
  disabled?: boolean;
  onDone?: () => void;
}) {
  const t = useTranslations("searchRunner");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);

  const isAdmin = Boolean(userId);
  const idleLabel = kind === "jobs" ? t("runJobs") : t("runPosts");
  const pendingLabel = t("running");

  async function start() {
    setPending(true);
    setError(null);
    setStatus(null);
    try {
      const runUrl = isAdmin
        ? kind === "jobs"
          ? `/api/admin/users/${encodeURIComponent(userId!)}/job-search/run`
          : `/api/admin/users/${encodeURIComponent(userId!)}/post-search/run`
        : kind === "jobs"
          ? "/api/job-search/run"
          : "/api/post-search/run";
      const body =
        kind === "jobs" ? { job_search_id: searchId } : { post_search_id: searchId };
      const runResp = await fetch(runUrl, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(body),
        cache: "no-store",
      });
      const runJson = (await runResp.json().catch(() => null)) as RunResponse | null;
      if (!runResp.ok || !runJson?.session_id) {
        throw new Error(runJson?.message || t(kind === "jobs" ? "errors.startJobs" : "errors.startPosts"));
      }
      setStatus(runJson.status ?? "running");

      const statusUrl = isAdmin
        ? kind === "jobs"
          ? `/api/admin/users/${encodeURIComponent(userId!)}/job-search/run/${encodeURIComponent(runJson.session_id)}`
          : `/api/admin/users/${encodeURIComponent(userId!)}/post-search/run/${encodeURIComponent(runJson.session_id)}`
        : kind === "jobs"
          ? `/api/job-search/run/${encodeURIComponent(runJson.session_id)}`
          : `/api/post-search/run/${encodeURIComponent(runJson.session_id)}`;

      for (let attempt = 0; attempt < 600; attempt += 1) {
        await sleep(1000);
        const stResp = await fetch(statusUrl, { cache: "no-store" });
        const stJson = (await stResp.json().catch(() => null)) as RunResponse | null;
        if (!stResp.ok || !stJson) throw new Error(t("errors.status"));
        setStatus(stJson.status ?? null);
        if (stJson.status === "done") {
          onDone?.();
          return;
        }
        if (stJson.status === "error" || stJson.status === "lost") {
          throw new Error(stJson.message || t(kind === "jobs" ? "errors.runJobs" : "errors.runPosts"));
        }
      }
      throw new Error(t("errors.timeout"));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t(kind === "jobs" ? "errors.startJobs" : "errors.startPosts"));
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="space-y-1">
      <Button type="button" onClick={() => void start()} disabled={pending || Boolean(disabled)} size="sm">
        {pending ? <RefreshCw className="size-4 animate-spin" /> : <Play className="size-4" />}
        {pending ? pendingLabel : idleLabel}
      </Button>
      {status ? (
        <div className="text-xs text-muted-foreground">
          {t("status")}: <span className={cn(status === "error" ? "text-destructive" : "")}>{status}</span>
        </div>
      ) : null}
      {error ? <div className="max-w-xs text-xs text-destructive">{error}</div> : null}
    </div>
  );
}
