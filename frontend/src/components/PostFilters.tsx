import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export type PostFilter = "all" | "relevant" | "rejected";

export type PostFilterCounts = {
  all: number;
  relevant: number;
  rejected: number;
  pending: number;
};

const FILTERS: { value: PostFilter; href: string; label: string; countKey: keyof Omit<PostFilterCounts, "pending"> }[] = [
  { value: "all", href: "/posts?filter=all", label: "Все", countKey: "all" },
  { value: "relevant", href: "/posts?filter=relevant", label: "Принято", countKey: "relevant" },
  { value: "rejected", href: "/posts?filter=rejected", label: "Отклонено", countKey: "rejected" },
];

export function PostFilters({
  filter,
  counts,
}: {
  filter: PostFilter;
  counts?: PostFilterCounts;
}) {
  return (
    <div className="inline-flex flex-wrap gap-2">
      {FILTERS.map((item) => {
        const active = filter === item.value;
        const count = counts?.[item.countKey];

        return (
          <Link
            key={item.value}
            href={item.href}
            className={cn(
              buttonVariants({
                variant: active ? "default" : "outline",
                size: "sm",
              }),
              "h-9 gap-2 rounded-full px-4",
            )}
          >
            {item.label}
            {typeof count === "number" ? (
              <span
                className={cn(
                  "inline-flex min-w-5 items-center justify-center rounded-full px-1.5 text-xs tabular-nums",
                  active
                    ? "bg-primary-foreground/15 text-primary-foreground"
                    : "bg-muted text-muted-foreground",
                )}
              >
                {count}
              </span>
            ) : null}
          </Link>
        );
      })}
    </div>
  );
}
