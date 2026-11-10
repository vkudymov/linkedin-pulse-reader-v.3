"use client";

import { useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import {
  BriefcaseBusiness,
  ChevronDown,
  FileText,
  Newspaper,
  ScrollText,
  Search,
  Settings,
  User,
  Users,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { Link, usePathname } from "@/i18n/navigation";
import { LocaleMenuButtons } from "@/components/LocaleSwitcher";
import { cn } from "@/lib/utils";

type NavActive = "posts" | "jobs" | "account" | "prompts" | "searches" | "admin";

type AdminSection = "users" | "searchRuns" | "searches" | "prompts" | "settings";

const ADMIN_NAV: {
  section: AdminSection;
  href: string;
  icon: LucideIcon;
  match: (path: string) => boolean;
}[] = [
  { section: "users", href: "/admin", icon: Users, match: (p) => p === "/admin" },
  {
    section: "searchRuns",
    href: "/admin/search-runs",
    icon: ScrollText,
    match: (p) => p.startsWith("/admin/search-runs"),
  },
  {
    section: "searches",
    href: "/admin/searches",
    icon: Search,
    match: (p) => p.startsWith("/admin/searches"),
  },
  {
    section: "prompts",
    href: "/admin/prompts",
    icon: FileText,
    match: (p) => p.startsWith("/admin/prompts"),
  },
  {
    section: "settings",
    href: "/admin/settings",
    icon: Settings,
    match: (p) => p.startsWith("/admin/settings"),
  },
];

function adminSectionFromPath(pathname: string): AdminSection | null {
  for (const item of ADMIN_NAV) {
    if (item.match(pathname)) return item.section;
  }
  return null;
}

function mainNavActive(
  pathname: string,
  active?: NavActive,
): { posts: boolean; jobs: boolean; prompts: boolean } {
  if (active === "posts" || active === "jobs" || active === "prompts") {
    return {
      posts: active === "posts",
      jobs: active === "jobs",
      prompts: active === "prompts",
    };
  }
  return {
    posts: pathname.startsWith("/posts"),
    jobs: pathname.startsWith("/jobs"),
    prompts: pathname === "/prompts" || pathname.startsWith("/prompts/"),
  };
}

function profileInitial(subtitle?: string | null): string | null {
  if (!subtitle?.includes("@")) return null;
  return subtitle.trim()[0].toUpperCase();
}

function NavItem({
  href,
  label,
  icon: Icon,
  active,
  compact,
}: {
  href: string;
  label: string;
  icon: LucideIcon;
  active: boolean;
  compact?: boolean;
}) {
  return (
    <Link
      href={href}
      title={label}
      className={cn(
        "group flex shrink-0 flex-col items-center gap-0.5 px-1 py-1 font-medium leading-tight sm:px-1.5",
        compact
          ? "w-[3.25rem] text-[0.6rem] sm:w-[3.75rem] sm:text-[0.65rem]"
          : "w-[4rem] text-[0.65rem] sm:w-[4.5rem] sm:text-xs",
        active ? "text-foreground" : "text-muted-foreground hover:text-foreground",
      )}
    >
      <Icon
        className={cn(compact ? "size-[1.125rem] sm:size-5" : "size-5 sm:size-6", active && "stroke-[2.25]")}
        strokeWidth={active ? 2.25 : 1.75}
        aria-hidden
      />
      <span className="max-w-full truncate text-center">{label}</span>
      <span
        className={cn(
          "mt-0.5 h-0.5 w-full max-w-[3.25rem] rounded-full transition-colors",
          active ? "bg-foreground" : "bg-transparent group-hover:bg-border",
        )}
        aria-hidden
      />
    </Link>
  );
}

function ProfileMenu({
  isAdmin,
  active,
  subtitle,
}: {
  isAdmin?: boolean;
  active?: NavActive;
  subtitle?: string | null;
}) {
  const t = useTranslations("nav");
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  const profileActive = active === "account";

  useEffect(() => {
    if (!open) return;
    function onPointerDown(e: MouseEvent) {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div ref={rootRef} className="relative shrink-0">
      <button
        type="button"
        aria-expanded={open}
        aria-haspopup="menu"
        onClick={() => setOpen((v) => !v)}
        className={cn(
          "group flex w-[4rem] shrink-0 flex-col items-center gap-0.5 px-1 py-1 text-[0.65rem] font-medium leading-tight sm:w-[4.5rem] sm:text-xs",
          profileActive ? "text-foreground" : "text-muted-foreground hover:text-foreground",
        )}
      >
        <span
          className={cn(
            "flex size-6 items-center justify-center rounded-full border text-[0.65rem] font-semibold sm:size-7 sm:text-xs",
            profileActive ? "border-foreground bg-muted" : "border-border bg-muted/50",
          )}
        >
          {profileInitial(subtitle) ?? <User className="size-3.5" strokeWidth={2} />}
        </span>
        <span className="flex items-center gap-0.5">
          {t("profile")}
          <ChevronDown
            className={cn("size-3 transition-transform", open && "rotate-180")}
            strokeWidth={2.5}
            aria-hidden
          />
        </span>
        <span
          className={cn(
            "mt-0.5 h-0.5 w-full max-w-[3.25rem] rounded-full",
            profileActive ? "bg-foreground" : "bg-transparent group-hover:bg-border",
          )}
          aria-hidden
        />
      </button>

      {open ? (
        <div
          role="menu"
          className="absolute right-0 top-full z-50 mt-1 w-56 overflow-hidden rounded-lg border border-border bg-popover text-popover-foreground shadow-lg"
        >
          <div className="py-1">
            <Link
              role="menuitem"
              href="/account"
              className="block px-4 py-2.5 text-sm hover:bg-muted"
              onClick={() => setOpen(false)}
            >
              {t("account")}
            </Link>
            {isAdmin ? (
              <Link
                role="menuitem"
                href="/admin"
                className="block px-4 py-2.5 text-sm hover:bg-muted"
                onClick={() => setOpen(false)}
              >
                {t("admin")}
              </Link>
            ) : null}
            <hr className="my-1 border-border/80" />
            <LocaleMenuButtons />
            <hr className="my-1 border-border/80" />
            <Link
              role="menuitem"
              href="/logout"
              className="block px-4 py-2.5 text-sm text-muted-foreground hover:bg-muted hover:text-foreground"
              onClick={() => setOpen(false)}
            >
              {t("logout")}
            </Link>
          </div>
        </div>
      ) : null}
    </div>
  );
}

export function AppHeader({
  title: _title,
  subtitle,
  active,
  isAdmin,
}: {
  title: string;
  subtitle?: string | null;
  active?: NavActive;
  isAdmin?: boolean;
}) {
  const t = useTranslations("nav");
  const tAdmin = useTranslations("admin.tabs");
  const pathname = usePathname();
  const adminSection = isAdmin ? adminSectionFromPath(pathname) : null;
  const mainActive = mainNavActive(pathname, active);

  return (
    <header className="sticky top-0 z-40 border-b border-border/90 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80">
      <div className={cn("mx-auto w-full max-w-6xl px-2 py-1 sm:px-3", isAdmin && "max-w-[min(100%,90rem)]")}>
        <div className="flex min-h-[3.25rem] items-center gap-1 sm:gap-2">
          <Link
            href="/posts"
            className="flex shrink-0 items-center pr-0.5 text-foreground sm:pr-1"
            aria-label={t("posts")}
          >
            <span className="flex size-8 items-center justify-center rounded-sm bg-[#0a66c2] text-sm font-bold text-white">
              in
            </span>
            <span className="hidden text-sm font-semibold tracking-tight text-foreground xl:inline xl:pl-1.5">
              Pulse
            </span>
          </Link>

          <nav
            className="flex min-w-0 flex-1 items-stretch justify-start gap-0 overflow-x-auto overscroll-x-contain [-ms-overflow-style:none] [scrollbar-width:none] sm:justify-center sm:gap-0.5 [&::-webkit-scrollbar]:hidden"
            aria-label={isAdmin ? `${t("mainMenu")}, ${t("adminMenu")}` : t("mainMenu")}
          >
            <NavItem
              href="/posts"
              label={t("posts")}
              icon={Newspaper}
              active={mainActive.posts}
              compact={isAdmin}
            />
            <NavItem
              href="/jobs"
              label={t("jobs")}
              icon={BriefcaseBusiness}
              active={mainActive.jobs}
              compact={isAdmin}
            />
            <NavItem
              href="/prompts"
              label={t("prompts")}
              icon={FileText}
              active={mainActive.prompts}
              compact={isAdmin}
            />
            {isAdmin ? (
              <>
                <span className="mx-0.5 w-px shrink-0 self-center bg-border" aria-hidden />
                {ADMIN_NAV.map((item) => (
                  <NavItem
                    key={item.section}
                    href={item.href}
                    label={tAdmin(item.section)}
                    icon={item.icon}
                    active={adminSection === item.section}
                    compact
                  />
                ))}
              </>
            ) : null}
          </nav>

          <ProfileMenu isAdmin={isAdmin} active={active} subtitle={subtitle} />
        </div>
      </div>
    </header>
  );
}
