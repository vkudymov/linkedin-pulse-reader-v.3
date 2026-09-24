"use client";

import { useTranslations } from "next-intl";

import { Label } from "@/components/ui/label";

const FORMATS = ["none", "xlsx", "docx", "txt", "json", "xml"] as const;

export function EmailReportFields({
  enabled,
  format,
  onEnabledChange,
  onFormatChange,
}: {
  enabled: boolean;
  format: string;
  onEnabledChange: (enabled: boolean) => void;
  onFormatChange: (format: string) => void;
}) {
  const t = useTranslations("emailReport");
  const value = FORMATS.includes(format as (typeof FORMATS)[number]) ? format : "none";
  return (
    <div className="md:col-span-2 grid grid-cols-1 gap-3 md:grid-cols-2">
      <div>
        <Label>{t("formatLabel")}</Label>
        <select
          className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
          value={value}
          onChange={(e) => {
            const next = e.target.value;
            onFormatChange(next);
            if (next === "none") onEnabledChange(false);
            else if (!enabled) onEnabledChange(true);
          }}
        >
          {FORMATS.map((fmt) => (
            <option key={fmt} value={fmt}>
              {t(`formats.${fmt}`)}
            </option>
          ))}
        </select>
      </div>
      <div className="flex items-end">
        <label className="flex items-center gap-2 pb-2 text-sm">
          <input
            type="checkbox"
            checked={enabled && value !== "none"}
            onChange={(e) => {
              const next = e.target.checked;
              onEnabledChange(next);
              if (next && value === "none") onFormatChange("xlsx");
              if (!next) onFormatChange("none");
            }}
          />
          {t("enabledLabel")}
        </label>
      </div>
    </div>
  );
}
