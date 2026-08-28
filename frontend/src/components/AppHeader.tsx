import Link from "next/link";

export function AppHeader({
  title,
  subtitle,
  active,
  isAdmin,
}: {
  title: string;
  subtitle?: string | null;
  active?: "posts" | "account" | "prompts" | "admin";
  isAdmin?: boolean;
}) {
  return (
    <header className="border-b border-border/80 bg-background">
      <div className="mx-auto flex max-w-3xl items-center justify-between gap-4 px-6 py-4">
        <div className="min-w-0">
          <h1 className="truncate text-base font-semibold tracking-tight">{title}</h1>
          {subtitle ? (
            <p className="text-sm text-muted-foreground">{subtitle}</p>
          ) : null}
        </div>
        <nav className="flex items-center gap-3">
          <Link
            className={[
              "text-sm underline-offset-4 hover:text-foreground hover:underline",
              active === "posts" ? "text-foreground" : "text-muted-foreground",
            ].join(" ")}
            href="/posts"
          >
            Посты
          </Link>
          <Link
            className={[
              "text-sm underline-offset-4 hover:text-foreground hover:underline",
              active === "prompts" ? "text-foreground" : "text-muted-foreground",
            ].join(" ")}
            href="/prompts"
          >
            Промпты
          </Link>
          <Link
            className={[
              "text-sm underline-offset-4 hover:text-foreground hover:underline",
              active === "account" ? "text-foreground" : "text-muted-foreground",
            ].join(" ")}
            href="/account"
          >
            Личный кабинет
          </Link>
          {isAdmin ? (
            <Link
              className={[
                "text-sm underline-offset-4 hover:text-foreground hover:underline",
                active === "admin" ? "text-foreground" : "text-muted-foreground",
              ].join(" ")}
              href="/admin"
            >
              Админ
            </Link>
          ) : null}
          <Link
            className="text-sm text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
            href="/logout"
          >
            Выйти
          </Link>
        </nav>
      </div>
    </header>
  );
}

