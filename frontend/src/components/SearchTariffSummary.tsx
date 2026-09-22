"use client";

import { useTranslations } from "next-intl";

import type { SearchTariffInfo } from "@/lib/searchTariffs";
import { cn } from "@/lib/utils";

const FALLBACK_POST = { max_scan_count: 10, target_found_count: 10, min_relevance_percent: 0 };
const FALLBACK_JOB = { max_scan_count: 25, target_found_count: 25, min_relevance_percent: 0 };

export function SearchTariffSummary({
  tariff,
  kind = "post",
  className,
}: {
  tariff: SearchTariffInfo | null;
  kind?: "post" | "job";
  className?: string;
}) {
  const t = useTranslations("searchTariff");
  const fallback = kind === "job" ? FALLBACK_JOB : FALLBACK_POST;
  const scan = tariff?.max_scan_count ?? fallback.max_scan_count;
  const found = tariff?.target_found_count ?? fallback.target_found_count;
  const min = tariff?.min_relevance_percent ?? fallback.min_relevance_percent;

  return (
    <div className={cn("space-y-1 text-xs text-muted-foreground", className)}>
      <div>
        <span className="font-medium text-foreground/80">{t("label")}:</span>{" "}
        <span>{tariff?.title || t("default")}</span>
      </div>
      <div>
        {t("fields.scan")}: <span className="text-foreground/80">{scan}</span>
      </div>
      <div>
        {t("fields.found")}: <span className="text-foreground/80">{found}</span>
      </div>
      <div>
        {t("fields.min")}: <span className="text-foreground/80">{min}</span>
      </div>
    </div>
  );
}
