"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { LinkedInFilterButton, LinkedInFilterRow } from "@/components/ui/linkedin-filter-chip";
import {
  PEOPLE_INDUSTRIES,
  PEOPLE_PROFILE_LANGUAGES,
  type NetworkCode,
  type PeopleFilters,
} from "@/lib/peopleFilters";

function TagField({
  label,
  values,
  placeholder,
  onChange,
}: {
  label: string;
  values: string[];
  placeholder: string;
  onChange: (next: string[]) => void;
}) {
  const [draft, setDraft] = useState("");

  function add(raw: string) {
    const item = raw.trim();
    if (!item) return;
    if (values.some((v) => v.toLowerCase() === item.toLowerCase())) {
      setDraft("");
      return;
    }
    onChange([...values, item]);
    setDraft("");
  }

  return (
    <div className="grid gap-2">
      <Label>{label}</Label>
      <Input
        value={draft}
        placeholder={placeholder}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === ",") {
            e.preventDefault();
            add(draft);
          }
        }}
        onBlur={() => add(draft)}
      />
      {values.length ? (
        <div className="flex flex-wrap gap-1.5">
          {values.map((value) => (
            <button
              key={value}
              type="button"
              className="inline-flex items-center gap-1 rounded-full border border-border px-2.5 py-0.5 text-xs"
              onClick={() => onChange(values.filter((v) => v !== value))}
            >
              {value}
              <X className="size-3" aria-hidden />
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}

export function AllFiltersDialog({
  open,
  value,
  onClose,
  onApply,
}: {
  open: boolean;
  value: PeopleFilters;
  onClose: () => void;
  onApply: (next: PeopleFilters) => void;
}) {
  const t = useTranslations("people.filters");
  const [draft, setDraft] = useState<PeopleFilters>(value);

  useEffect(() => {
    if (open) setDraft(value);
  }, [open, value]);

  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  function toggleNetwork(code: NetworkCode) {
    setDraft((cur) => ({
      ...cur,
      network: cur.network.includes(code)
        ? cur.network.filter((c) => c !== code)
        : [...cur.network, code],
    }));
  }

  function toggleIndustry(id: string) {
    setDraft((cur) => ({
      ...cur,
      industry: cur.industry.includes(id)
        ? cur.industry.filter((x) => x !== id)
        : [...cur.industry, id],
    }));
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/40 p-4 pt-[10vh]">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="people-all-filters-title"
        className="w-full max-w-xl rounded-2xl border border-border bg-background p-6 shadow-xl"
      >
        <div className="mb-4 flex items-start justify-between gap-3">
          <div>
            <h3 id="people-all-filters-title" className="text-base font-semibold">
              {t("title")}
            </h3>
            <p className="mt-1 text-sm text-muted-foreground">{t("description")}</p>
          </div>
          <button type="button" onClick={onClose} className="rounded-full p-1 text-muted-foreground hover:bg-muted">
            <X className="size-4" />
          </button>
        </div>

        <div className="grid gap-4">
          <div className="grid gap-2">
            <Label>{t("network")}</Label>
            <LinkedInFilterRow>
              <LinkedInFilterButton active={draft.network.includes("F")} onClick={() => toggleNetwork("F")}>
                {t("network1")}
              </LinkedInFilterButton>
              <LinkedInFilterButton active={draft.network.includes("S")} onClick={() => toggleNetwork("S")}>
                {t("network2")}
              </LinkedInFilterButton>
              <LinkedInFilterButton active={draft.network.includes("O")} onClick={() => toggleNetwork("O")}>
                {t("network3")}
              </LinkedInFilterButton>
            </LinkedInFilterRow>
          </div>

          <TagField
            label={t("locations")}
            values={draft.locations}
            placeholder={t("locationsPlaceholder")}
            onChange={(locations) => setDraft((cur) => ({ ...cur, locations }))}
          />
          <TagField
            label={t("currentCompany")}
            values={draft.current_company}
            placeholder={t("companyPlaceholder")}
            onChange={(current_company) => setDraft((cur) => ({ ...cur, current_company }))}
          />
          <TagField
            label={t("pastCompany")}
            values={draft.past_company}
            placeholder={t("companyPlaceholder")}
            onChange={(past_company) => setDraft((cur) => ({ ...cur, past_company }))}
          />
          <TagField
            label={t("school")}
            values={draft.school}
            placeholder={t("schoolPlaceholder")}
            onChange={(school) => setDraft((cur) => ({ ...cur, school }))}
          />

          <div className="grid gap-2">
            <Label>{t("industry")}</Label>
            <select
              className="h-10 rounded-xl border border-border bg-background px-3 text-sm"
              value=""
              onChange={(e) => {
                if (e.target.value) toggleIndustry(e.target.value);
              }}
            >
              <option value="">{t("industryPlaceholder")}</option>
              {PEOPLE_INDUSTRIES.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.label}
                </option>
              ))}
            </select>
            {draft.industry.length ? (
              <div className="flex flex-wrap gap-1.5">
                {draft.industry.map((id) => {
                  const label = PEOPLE_INDUSTRIES.find((item) => item.id === id)?.label || id;
                  return (
                    <button
                      key={id}
                      type="button"
                      className="inline-flex items-center gap-1 rounded-full border border-border px-2.5 py-0.5 text-xs"
                      onClick={() => toggleIndustry(id)}
                    >
                      {label}
                      <X className="size-3" aria-hidden />
                    </button>
                  );
                })}
              </div>
            ) : null}
          </div>

          <div className="grid gap-2">
            <Label>{t("language")}</Label>
            <select
              className="h-10 rounded-xl border border-border bg-background px-3 text-sm"
              value={draft.profile_language}
              onChange={(e) => setDraft((cur) => ({ ...cur, profile_language: e.target.value }))}
            >
              <option value="">{t("languageAny")}</option>
              {PEOPLE_PROFILE_LANGUAGES.map((code) => (
                <option key={code} value={code}>
                  {code}
                </option>
              ))}
            </select>
          </div>

          <div className="grid gap-2">
            <Label>{t("keywords")}</Label>
            <Input
              value={draft.keywords}
              onChange={(e) => setDraft((cur) => ({ ...cur, keywords: e.target.value }))}
              placeholder={t("keywordsPlaceholder")}
            />
          </div>
        </div>

        <div className="mt-6 flex flex-wrap justify-end gap-2">
          <Button type="button" variant="outline" className="h-9 rounded-full" onClick={onClose}>
            {t("cancel")}
          </Button>
          <Button
            type="button"
            className="h-9 rounded-full"
            onClick={() => {
              onApply(draft);
              onClose();
            }}
          >
            {t("apply")}
          </Button>
        </div>
      </div>
    </div>
  );
}
