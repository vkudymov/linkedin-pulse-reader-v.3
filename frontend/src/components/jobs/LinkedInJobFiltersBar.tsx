"use client";

import { useTranslations } from "next-intl";

import { cn } from "@/lib/utils";
import {
  type DatePostedFilter,
  type EmploymentFilter,
  type ExperienceFilter,
  type LinkedInJobFilters,
} from "@/lib/linkedinJobFilters";

function pillClass(active: boolean, disabled?: boolean) {
  return cn(
    "inline-flex h-9 items-center rounded-full border px-3 text-sm",
    active
      ? "border-foreground bg-foreground text-background"
      : "border-border bg-background text-foreground",
    disabled ? "cursor-default opacity-80" : "cursor-pointer",
  );
}

function selectClass(active: boolean, disabled?: boolean) {
  return cn(pillClass(active, disabled), disabled && "pointer-events-none");
}

export function LinkedInJobFiltersBar({
  value,
  onChange,
  disabled,
}: {
  value: LinkedInJobFilters;
  onChange: (next: LinkedInJobFilters) => void;
  disabled?: boolean;
}) {
  const t = useTranslations("jobs.prompts.linkedinFilters");

  function toggle(key: "remote" | "easy_apply") {
    onChange({ ...value, [key]: !value[key] });
  }

  return (
    <div className="grid gap-2">
      <div className="text-sm font-medium">{t("title")}</div>
      <div className="flex flex-wrap gap-2">
        <select
          className={selectClass(value.date_posted !== "any", disabled)}
          value={value.date_posted}
          disabled={disabled}
          onChange={(e) =>
            onChange({ ...value, date_posted: e.target.value as DatePostedFilter })
          }
        >
          <option value="any">{t("datePosted.any")}</option>
          <option value="day">{t("datePosted.day")}</option>
          <option value="week">{t("datePosted.week")}</option>
          <option value="month">{t("datePosted.month")}</option>
        </select>

        <button
          type="button"
          className={pillClass(value.remote, disabled)}
          disabled={disabled}
          onClick={() => toggle("remote")}
        >
          {t("remote")}
        </button>

        <button
          type="button"
          className={pillClass(value.easy_apply, disabled)}
          disabled={disabled}
          onClick={() => toggle("easy_apply")}
        >
          {t("easyApply")}
        </button>

        <select
          className={selectClass(value.experience !== "any", disabled)}
          value={value.experience}
          disabled={disabled}
          onChange={(e) =>
            onChange({ ...value, experience: e.target.value as ExperienceFilter })
          }
        >
          <option value="any">{t("experience.any")}</option>
          <option value="internship">{t("experience.internship")}</option>
          <option value="entry">{t("experience.entry")}</option>
          <option value="associate">{t("experience.associate")}</option>
          <option value="mid_senior">{t("experience.midSenior")}</option>
          <option value="director">{t("experience.director")}</option>
          <option value="executive">{t("experience.executive")}</option>
        </select>

        <select
          className={selectClass(value.employment !== "any", disabled)}
          value={value.employment}
          disabled={disabled}
          onChange={(e) =>
            onChange({ ...value, employment: e.target.value as EmploymentFilter })
          }
        >
          <option value="any">{t("employment.any")}</option>
          <option value="full_time">{t("employment.fullTime")}</option>
          <option value="part_time">{t("employment.partTime")}</option>
          <option value="contract">{t("employment.contract")}</option>
          <option value="temporary">{t("employment.temporary")}</option>
          <option value="internship">{t("employment.internship")}</option>
        </select>

        <input
          className={cn(
            pillClass(Boolean(value.company.trim()), disabled),
            "w-40 min-w-32 outline-none",
          )}
          value={value.company}
          disabled={disabled}
          placeholder={t("company")}
          onChange={(e) => onChange({ ...value, company: e.target.value })}
        />
      </div>
      <p className="text-xs text-muted-foreground">{t("hint")}</p>
    </div>
  );
}
