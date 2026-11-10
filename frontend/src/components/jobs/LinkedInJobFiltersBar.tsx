"use client";

import { useTranslations } from "next-intl";

import {
  LinkedInFilterButton,
  LinkedInFilterRow,
  LinkedInFilterSelect,
  linkedinFilterChipClass,
} from "@/components/ui/linkedin-filter-chip";
import { cn } from "@/lib/utils";
import {
  type DatePostedFilter,
  type EmploymentFilter,
  type ExperienceFilter,
  type LinkedInJobFilters,
} from "@/lib/linkedinJobFilters";

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
      <LinkedInFilterRow>
        <LinkedInFilterSelect
          active={value.date_posted !== "any"}
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
        </LinkedInFilterSelect>

        <LinkedInFilterButton
          active={value.remote}
          disabled={disabled}
          onClick={() => toggle("remote")}
        >
          {t("remote")}
        </LinkedInFilterButton>

        <LinkedInFilterButton
          active={value.easy_apply}
          disabled={disabled}
          onClick={() => toggle("easy_apply")}
        >
          {t("easyApply")}
        </LinkedInFilterButton>

        <LinkedInFilterSelect
          active={value.experience !== "any"}
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
        </LinkedInFilterSelect>

        <LinkedInFilterSelect
          active={value.employment !== "any"}
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
        </LinkedInFilterSelect>

        <input
          className={cn(
            linkedinFilterChipClass(Boolean(value.company.trim()), disabled),
            "w-36 min-w-[8rem] outline-none placeholder:font-normal placeholder:text-muted-foreground",
            value.company.trim() ? "placeholder:text-white/70" : "",
          )}
          value={value.company}
          disabled={disabled}
          placeholder={t("company")}
          onChange={(e) => onChange({ ...value, company: e.target.value })}
        />
      </LinkedInFilterRow>
      <p className="text-xs text-muted-foreground">{t("hint")}</p>
    </div>
  );
}
