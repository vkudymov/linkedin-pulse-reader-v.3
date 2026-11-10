"use client";

import { useTranslations } from "next-intl";

import {
  LinkedInFilterLink,
  LinkedInFilterRow,
} from "@/components/ui/linkedin-filter-chip";

export type PostFilter = "all" | "relevant" | "rejected";

export type PostFilterCounts = {
  all: number;
  relevant: number;
  rejected: number;
  pending: number;
};

const FILTERS: {
  value: PostFilter;
  href: string;
  labelKey: "all" | "relevant" | "rejected";
  countKey: keyof Omit<PostFilterCounts, "pending">;
}[] = [
  { value: "all", href: "/posts?filter=all", labelKey: "all", countKey: "all" },
  { value: "relevant", href: "/posts?filter=relevant", labelKey: "relevant", countKey: "relevant" },
  { value: "rejected", href: "/posts?filter=rejected", labelKey: "rejected", countKey: "rejected" },
];

export function PostFilters({
  filter,
  counts,
}: {
  filter: PostFilter;
  counts?: PostFilterCounts;
}) {
  const t = useTranslations("posts.filters");
  return (
    <LinkedInFilterRow>
      {FILTERS.map((item) => {
        const active = filter === item.value;
        const count = counts?.[item.countKey];

        return (
          <LinkedInFilterLink
            key={item.value}
            href={item.href}
            active={active}
            count={typeof count === "number" ? count : undefined}
          >
            {t(item.labelKey)}
          </LinkedInFilterLink>
        );
      })}
    </LinkedInFilterRow>
  );
}
