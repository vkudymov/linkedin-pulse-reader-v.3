"use client";

import { useEffect, useMemo, useState } from "react";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

type TariffRow = {
  id: string;
  title: string;
  max_scan_count: number;
  target_found_count: number;
  min_relevance_percent: number;
  email_reports_enabled: boolean;
  sort_order: number;
  created_at?: string | null;
  updated_at?: string | null;
};

const fieldClassName =
  "h-11 rounded-full border-border/80 bg-secondary px-4 text-sm text-foreground shadow-none";

function asInt(v: string, fallback: number) {
  const n = Number(v);
  return Number.isFinite(n) ? Math.trunc(n) : fallback;
}

export function AdminSearchTariffsPanel() {
  const t = useTranslations("adminSettings");
  const [rows, setRows] = useState<TariffRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [savingId, setSavingId] = useState<string | null>(null);

  const [draftTitle, setDraftTitle] = useState("");
  const [draftScan, setDraftScan] = useState("25");
  const [draftFound, setDraftFound] = useState("10");
  const [draftMin, setDraftMin] = useState("70");
  const [draftOrder, setDraftOrder] = useState("0");
  const [draftEmailReportsEnabled, setDraftEmailReportsEnabled] = useState(false);

  const canDelete = useMemo(() => rows.length > 1, [rows.length]);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const resp = await fetch("/api/admin/search-tariffs", { method: "GET", cache: "no-store" });
      const json = (await resp.json().catch(() => null)) as unknown;
      if (!resp.ok || !Array.isArray(json)) throw new Error(t("errors.load"));
      setRows(
        (json as Record<string, unknown>[]).map((r) => ({
          ...(r as TariffRow),
          email_reports_enabled: Boolean((r as { email_reports_enabled?: unknown }).email_reports_enabled),
        })),
      );
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t("errors.load"));
      setRows([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const handle = window.setTimeout(() => {
      void load();
    }, 0);
    return () => window.clearTimeout(handle);
  }, []);

  async function saveAll(row: TariffRow) {
    setSavingId(row.id);
    setError(null);
    try {
      const resp = await fetch(`/api/admin/search-tariffs/${encodeURIComponent(row.id)}`, {
        method: "PATCH",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          title: row.title,
          max_scan_count: row.max_scan_count,
          target_found_count: row.target_found_count,
          min_relevance_percent: row.min_relevance_percent,
          email_reports_enabled: row.email_reports_enabled,
          sort_order: row.sort_order,
        }),
      });
      const json = (await resp.json().catch(() => null)) as unknown;
      if (!resp.ok || !json || typeof json !== "object") throw new Error(t("errors.save"));
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t("errors.save"));
    } finally {
      setSavingId(null);
    }
  }

  async function onDelete(id: string) {
    setError(null);
    try {
      const resp = await fetch(`/api/admin/search-tariffs/${encodeURIComponent(id)}`, { method: "DELETE" });
      if (!resp.ok) {
        const text = await resp.text().catch(() => "");
        throw new Error(text || t("errors.delete"));
      }
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t("errors.delete"));
    }
  }

  async function onCreate() {
    setError(null);
    try {
      const payload = {
        title: draftTitle.trim(),
        max_scan_count: asInt(draftScan, 25),
        target_found_count: asInt(draftFound, 10),
        min_relevance_percent: asInt(draftMin, 70),
        email_reports_enabled: draftEmailReportsEnabled,
        sort_order: asInt(draftOrder, 0),
      };
      const resp = await fetch("/api/admin/search-tariffs", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(payload),
      });
      const json = (await resp.json().catch(() => null)) as unknown;
      if (!resp.ok || !json || typeof json !== "object") throw new Error(t("errors.create"));
      setCreateOpen(false);
      setDraftTitle("");
      setDraftEmailReportsEnabled(false);
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t("errors.create"));
    }
  }

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-border bg-card p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-base font-semibold">{t("tabs.search")}</h2>
            <p className="mt-1 text-sm text-muted-foreground">{t("tariffs.hint")}</p>
          </div>
          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="outline"
              className="rounded-full"
              onClick={() => void load()}
              disabled={loading}
            >
              {t("actions.refresh")}
            </Button>
            <Button type="button" className="rounded-full" onClick={() => setCreateOpen((v) => !v)}>
              {t("actions.newTariff")}
            </Button>
          </div>
        </div>
        {error ? <p className="mt-3 text-sm text-destructive">{error}</p> : null}

        {createOpen ? (
          <div className="mt-5 rounded-2xl border border-border/80 bg-muted/30 p-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2 sm:col-span-2">
                <Label>{t("tariffs.fields.title")}</Label>
                <Input className={fieldClassName} value={draftTitle} onChange={(e) => setDraftTitle(e.target.value)} />
              </div>
              <div className="flex items-center gap-3 sm:col-span-2">
                <input
                  id="draft_email_reports_enabled"
                  type="checkbox"
                  checked={draftEmailReportsEnabled}
                  onChange={(e) => setDraftEmailReportsEnabled(e.target.checked)}
                />
                <Label htmlFor="draft_email_reports_enabled">{t("tariffs.fields.emailReports")}</Label>
              </div>
              <div className="space-y-2">
                <Label>{t("tariffs.fields.scan")}</Label>
                <Input className={fieldClassName} value={draftScan} onChange={(e) => setDraftScan(e.target.value)} />
              </div>
              <div className="space-y-2">
                <Label>{t("tariffs.fields.found")}</Label>
                <Input className={fieldClassName} value={draftFound} onChange={(e) => setDraftFound(e.target.value)} />
              </div>
              <div className="space-y-2">
                <Label>{t("tariffs.fields.min")}</Label>
                <Input className={fieldClassName} value={draftMin} onChange={(e) => setDraftMin(e.target.value)} />
              </div>
              <div className="space-y-2">
                <Label>{t("tariffs.fields.order")}</Label>
                <Input className={fieldClassName} value={draftOrder} onChange={(e) => setDraftOrder(e.target.value)} />
              </div>
            </div>
            <div className="mt-4 flex items-center gap-2">
              <Button type="button" className="rounded-full" onClick={() => void onCreate()}>
                {t("actions.create")}
              </Button>
              <Button type="button" variant="outline" className="rounded-full" onClick={() => setCreateOpen(false)}>
                {t("actions.cancel")}
              </Button>
            </div>
          </div>
        ) : null}
      </div>

      <div className="space-y-3">
        {rows.map((r) => (
          <div key={r.id} className="rounded-2xl border border-border bg-card p-5">
            <div className="space-y-3">
              <div className="space-y-2">
                <Label>{t("tariffs.fields.title")}</Label>
                <Input
                  className={fieldClassName}
                  value={r.title}
                  onChange={(e) => setRows((prev) => prev.map((x) => (x.id === r.id ? { ...x, title: e.target.value } : x)))}
                />
              </div>
              <div className="flex items-center gap-3">
                <input
                  id={`email_reports_enabled_${r.id}`}
                  type="checkbox"
                  checked={Boolean(r.email_reports_enabled)}
                  onChange={(e) =>
                    setRows((prev) =>
                      prev.map((x) => (x.id === r.id ? { ...x, email_reports_enabled: e.target.checked } : x)),
                    )
                  }
                />
                <Label htmlFor={`email_reports_enabled_${r.id}`}>{t("tariffs.fields.emailReports")}</Label>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label>{t("tariffs.fields.scan")}</Label>
                  <Input
                    className={fieldClassName}
                    value={String(r.max_scan_count)}
                    onChange={(e) =>
                      setRows((prev) => prev.map((x) => (x.id === r.id ? { ...x, max_scan_count: asInt(e.target.value, x.max_scan_count) } : x)))
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label>{t("tariffs.fields.found")}</Label>
                  <Input
                    className={fieldClassName}
                    value={String(r.target_found_count)}
                    onChange={(e) =>
                      setRows((prev) => prev.map((x) => (x.id === r.id ? { ...x, target_found_count: asInt(e.target.value, x.target_found_count) } : x)))
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label>{t("tariffs.fields.min")}</Label>
                  <Input
                    className={fieldClassName}
                    value={String(r.min_relevance_percent)}
                    onChange={(e) =>
                      setRows((prev) =>
                        prev.map((x) => (x.id === r.id ? { ...x, min_relevance_percent: asInt(e.target.value, x.min_relevance_percent) } : x)),
                      )
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label>{t("tariffs.fields.order")}</Label>
                  <Input
                    className={fieldClassName}
                    value={String(r.sort_order)}
                    onChange={(e) =>
                      setRows((prev) => prev.map((x) => (x.id === r.id ? { ...x, sort_order: asInt(e.target.value, x.sort_order) } : x)))
                    }
                  />
                </div>
              </div>
              <p className="text-sm text-muted-foreground">
                {t("tariffs.preview", {
                  scan: r.max_scan_count,
                  found: r.target_found_count,
                  min: r.min_relevance_percent,
                })}
              </p>
              <div className="flex flex-wrap items-center gap-2">
                <Button
                  type="button"
                  className="rounded-full"
                  disabled={savingId === r.id}
                  onClick={() => void saveAll(r)}
                >
                  {savingId === r.id ? t("actions.saving") : t("actions.save")}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  className={cn("rounded-full", !canDelete && "opacity-50")}
                  disabled={!canDelete || savingId === r.id}
                  onClick={() => void onDelete(r.id)}
                >
                  {t("actions.delete")}
                </Button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
