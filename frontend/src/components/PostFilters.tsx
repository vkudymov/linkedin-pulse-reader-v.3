import Link from "next/link";

export type PostFilter = "all" | "relevant" | "rejected";

function FilterLink({
  href,
  active,
  children,
}: {
  href: string;
  active: boolean;
  children: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      className={[
        "rounded-xl border px-3 py-1.5 text-sm",
        active
          ? "border-zinc-900 bg-zinc-900 text-white"
          : "border-zinc-200 bg-white text-zinc-900 hover:bg-zinc-50",
      ].join(" ")}
    >
      {children}
    </Link>
  );
}

export function PostFilters({ filter }: { filter: PostFilter }) {
  return (
    <div className="flex flex-wrap gap-2">
      <FilterLink href="/posts?filter=all" active={filter === "all"}>
        Все
      </FilterLink>
      <FilterLink href="/posts?filter=relevant" active={filter === "relevant"}>
        Принято
      </FilterLink>
      <FilterLink href="/posts?filter=rejected" active={filter === "rejected"}>
        Отклонено
      </FilterLink>
    </div>
  );
}

