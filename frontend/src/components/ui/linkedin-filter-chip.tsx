"use client";

import type { ComponentProps, ReactNode } from "react";
import { ChevronDown } from "lucide-react";

import { Link } from "@/i18n/navigation";
import { cn } from "@/lib/utils";

/** LinkedIn Jobs search filter pill (light UI). */
export function linkedinFilterChipClass(active?: boolean, disabled?: boolean) {
  return cn(
    "inline-flex h-8 max-w-full shrink-0 items-center gap-1.5 rounded-full px-3 text-sm font-semibold",
    "transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-[#0a66c2]",
    active
      ? "border border-[#01754f] bg-[#01754f] text-white hover:bg-[#016b48]"
      : "border border-[#606060] bg-transparent text-foreground hover:bg-black/[0.04] dark:border-border dark:hover:bg-muted/50",
    disabled && "pointer-events-none opacity-50",
  );
}

export function LinkedInFilterCount({ active, children }: { active: boolean; children: ReactNode }) {
  return (
    <span
      className={cn(
        "inline-flex min-w-5 items-center justify-center rounded-full px-1.5 text-xs font-semibold tabular-nums",
        active ? "bg-white/25 text-white" : "bg-muted text-muted-foreground",
      )}
    >
      {children}
    </span>
  );
}

export function LinkedInFilterLink({
  href,
  active,
  children,
  count,
  className,
}: {
  href: string;
  active: boolean;
  children: ReactNode;
  count?: number;
  className?: string;
}) {
  return (
    <Link href={href} className={cn(linkedinFilterChipClass(active), className)}>
      {children}
      {typeof count === "number" ? <LinkedInFilterCount active={active}>{count}</LinkedInFilterCount> : null}
    </Link>
  );
}

export function LinkedInFilterButton({
  active,
  disabled,
  className,
  children,
  ...props
}: ComponentProps<"button"> & { active?: boolean }) {
  return (
    <button
      type="button"
      disabled={disabled}
      className={cn(linkedinFilterChipClass(active, disabled), className)}
      {...props}
    >
      {children}
    </button>
  );
}

export function LinkedInFilterSelect({
  active,
  disabled,
  className,
  children,
  ...props
}: ComponentProps<"select"> & { active?: boolean }) {
  return (
    <span className="relative inline-flex max-w-full">
      <select
        disabled={disabled}
        className={cn(linkedinFilterChipClass(active, disabled), "appearance-none pr-7", className)}
        {...props}
      >
        {children}
      </select>
      <ChevronDown
        aria-hidden
        className={cn(
          "pointer-events-none absolute top-1/2 right-2 size-3.5 -translate-y-1/2",
          active ? "text-white" : "text-foreground",
        )}
        strokeWidth={2.5}
      />
    </span>
  );
}

export function LinkedInFilterInput({
  active,
  className,
  ...props
}: ComponentProps<"input"> & { active?: boolean }) {
  const filled = Boolean(String(props.value ?? "").trim());
  const isActive = active ?? filled;
  return (
    <input
      className={cn(
        linkedinFilterChipClass(isActive, props.disabled),
        "min-w-[8rem] font-normal outline-none placeholder:font-normal",
        isActive ? "placeholder:text-white/70" : "placeholder:text-muted-foreground",
        className,
      )}
      {...props}
    />
  );
}

export function linkedinSelectFiltered(value: string, emptyValues: string[] = ["", "all"]) {
  return !emptyValues.includes(value);
}

export function LinkedInFilterRow({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn("flex flex-wrap items-center gap-2", className)}>{children}</div>;
}
