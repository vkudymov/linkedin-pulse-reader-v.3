"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Play, RefreshCw } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";

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

export function PostSearchRunner({
  runUrl = "/api/post-search/run",
  statusUrl = (sessionId: string) => `/api/post-search/run/${encodeURIComponent(sessionId)}`,
  redirectOnSuccess = true,
  successMessage,
  onSuccess,
}: {
  runUrl?: string;
  statusUrl?: (sessionId: string) => string;
  redirectOnSuccess?: boolean;
  successMessage?: string;
  onSuccess?: () => void;
}) {
  const router = useRouter();
  const locale = useLocale();
  const t = useTranslations("postSearch");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [status, setStatus] = useState<RunResponse["status"] | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const buttonLabel = pending ? t("button.pending") : t("button.idle");

  async function start() {
    setPending(true);
    setError(null);
    setSuccess(null);
    setStatus(null);
    setMessage(null);

    try {
      const runResp = await fetch(runUrl, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({}),
      });
      const runJson = (await runResp.json().catch(() => null)) as RunResponse | null;
      if (!runResp.ok || !runJson?.session_id) {
        throw new Error(runJson?.message || t("errors.startFailed"));
      }

      setStatus(runJson.status);
      setMessage(runJson.message ?? null);

      // Poll status until done/error.
      for (let attempt = 0; attempt < 600; attempt += 1) {
        await sleep(1000);
        const stResp = await fetch(statusUrl(runJson.session_id));
        const stJson = (await stResp.json().catch(() => null)) as RunResponse | null;
        if (!stResp.ok || !stJson) {
          throw new Error(t("errors.statusFailed"));
        }
        setStatus(stJson.status);
        setMessage(stJson.message ?? null);

        if (stJson.status === "done") {
          const okMessage = successMessage ?? t("successDefault");
          setSuccess(redirectOnSuccess ? t("successRedirecting") : okMessage);
          onSuccess?.();
          if (redirectOnSuccess) {
            // Give UI a moment to render success.
            await sleep(300);
            router.push("/posts");
            router.refresh();
          }
          return;
        }
        if (stJson.status === "error") {
          throw new Error(stJson.message || t("errors.runFailed"));
        }
      }

      throw new Error(t("errors.timeout"));
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : t("errors.startFailed");
      setError(msg);
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="space-y-1">
          <h3 className="text-base font-semibold">{t("title")}</h3>
          <p className="text-sm leading-6 text-muted-foreground">
            {t("description")}
          </p>
        </div>

        <Button
          type="button"
          onClick={start}
          disabled={pending}
          className="h-10 rounded-full"
        >
          {pending ? <RefreshCw className="mr-2 h-4 w-4 animate-spin" /> : <Play className="mr-2 h-4 w-4" />}
          {buttonLabel}
        </Button>
      </div>

      {status || message ? (
        <div className="rounded-xl border border-border/80 bg-muted/40 px-4 py-3 text-sm text-muted-foreground">
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <span className="font-medium text-foreground">{t("statusLabel")}</span>
            <span className={cn(status === "error" ? "text-destructive" : "")}>{status || "—"}</span>
          </div>
          {message ? <div className="mt-1 whitespace-pre-wrap">{message}</div> : null}
        </div>
      ) : null}

      {error ? (
        <div className="rounded-xl border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      ) : null}

      {success ? (
        <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-600 dark:text-emerald-300">
          {success}
        </div>
      ) : null}
    </div>
  );
}

