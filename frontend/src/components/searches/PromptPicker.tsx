"use client";

import { Link } from "@/i18n/navigation";
import { buttonVariants } from "@/components/ui/button";
import { Label } from "@/components/ui/label";

export type PromptOption = {
  id: string;
  role: "filter" | "search" | "comment" | string;
  title: string;
  body?: string;
  user_id?: string;
};

export function PromptPicker({
  label,
  value,
  options,
  fallbackBody,
  emptyLabel,
  editLabel,
  editHref,
  loading,
  onChange,
}: {
  label: string;
  value: string;
  options: PromptOption[];
  fallbackBody?: string | null;
  emptyLabel: string;
  editLabel?: string;
  editHref?: { pathname: "/prompts" | "/admin/prompts"; query?: Record<string, string> };
  loading?: boolean;
  onChange: (id: string) => void;
}) {
  const selected = options.find((p) => p.id === value);
  const body = (selected?.body || fallbackBody || "").trim();
  const href =
    editHref ??
    (editLabel && value ? { pathname: "/prompts" as const, query: { id: value } } : undefined);
  return (
    <div className="md:col-span-2">
      <div className="flex flex-wrap items-end gap-2">
        <div className="min-w-[220px] flex-1">
          <Label>{label}</Label>
          <select
            className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
            value={value}
            disabled={loading}
            onChange={(e) => onChange(e.target.value)}
          >
            <option value="">{loading ? "…" : emptyLabel}</option>
            {options.map((p) => (
              <option key={p.id} value={p.id}>
                {p.title || p.id}
              </option>
            ))}
          </select>
        </div>
        {value && href && editLabel ? (
          <Link href={href} className={buttonVariants({ variant: "outline", size: "sm" })}>
            {editLabel}
          </Link>
        ) : null}
      </div>
      {body ? (
        <pre className="mt-2 max-h-56 overflow-auto whitespace-pre-wrap rounded-md border border-border bg-background px-3 py-2 font-mono text-xs">
          {body}
        </pre>
      ) : null}
    </div>
  );
}
