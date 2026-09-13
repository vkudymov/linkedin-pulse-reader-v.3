"use client";

import { useState } from "react";
import { Play, RefreshCw } from "lucide-react";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type RunResponse = {
  session_id: string;
  status: "running" | "done" | "error" | string;
  message?: string | null;
};

async function sleep(ms: number) {
  await new Promise((r) => setTimeout(r, ms));
}

export function JobSearchRunButton({
  jobSearchId,
  disabled,
  limit = 25,
  onDone,
}: {
  jobSearchId: string;
  disabled?: boolean;
  limit?: number;
  onDone?: () => void;
}) {
  const t = useTranslations("jobs.runner");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<RunResponse["status"] | null>(null);

  async function start() {
    setPending(true);
    setError(null);
    setStatus(null);

    try {
      const runResp = await fetch("/api/job-search/run", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ job_search_id: jobSearchId, limit }),
      });
      const runJson = (await runResp.json().catch(() => null)) as RunResponse | null;
      if (!runResp.ok || !runJson?.session_id) {
        throw new Error(runJson?.message || t("errors.startFailed"));
      }

      setStatus(runJson.status);

      for (let attempt = 0; attempt < 600; attempt += 1) {
        await sleep(1000);
        const stResp = await fetch(
          `/api/job-search/run/${encodeURIComponent(runJson.session_id)}`,
        );
        const stJson = (await stResp.json().catch(() => null)) as RunResponse | null;
        if (!stResp.ok || !stJson) throw new Error(t("errors.statusFailed"));
        setStatus(stJson.status);
        if (stJson.status === "done") {
          onDone?.();
          return;
        }
        if (stJson.status === "error") throw new Error(stJson.message || t("errors.runFailed"));
      }

      throw new Error(t("errors.timeout"));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t("errors.startFailed"));
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="space-y-2">
      <Button
        type="button"
        onClick={start}
        disabled={pending || Boolean(disabled)}
        className="h-9 rounded-full"
      >
        {pending ? (
          <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
        ) : (
          <Play className="mr-2 h-4 w-4" />
        )}
        {pending ? t("pending") : t("idle")}
      </Button>

      {status ? (
        <div className="text-xs text-muted-foreground">
          <span className="font-medium text-foreground">{t("statusLabel")}</span>{" "}
          <span className={cn(status === "error" ? "text-destructive" : "")}>{status}</span>
        </div>
      ) : null}

      {error ? <div className="text-xs text-destructive">{error}</div> : null}
    </div>
  );
}

