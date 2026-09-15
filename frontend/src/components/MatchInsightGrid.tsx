export function asStringList(v: unknown): string[] {
  if (!Array.isArray(v)) return [];
  return v.filter((x): x is string => typeof x === "string" && x.trim().length > 0);
}

function ReqList({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="rounded-xl border border-border/80 bg-background/40 px-4 py-3">
      <div className="text-sm font-medium">{title}</div>
      {items.length ? (
        <ul className="mt-2 space-y-1 text-sm text-muted-foreground">
          {items.slice(0, 8).map((x) => (
            <li key={x} className="truncate">
              {x}
            </li>
          ))}
        </ul>
      ) : (
        <div className="mt-2 text-sm text-muted-foreground">—</div>
      )}
    </div>
  );
}

export function MatchInsightGrid({
  matchedTitle,
  missingTitle,
  redFlagsTitle,
  matched,
  missing,
  redFlags,
}: {
  matchedTitle: string;
  missingTitle: string;
  redFlagsTitle: string;
  matched: unknown;
  missing: unknown;
  redFlags: unknown;
}) {
  return (
    <div className="grid gap-3 sm:grid-cols-3">
      <ReqList title={matchedTitle} items={asStringList(matched)} />
      <ReqList title={missingTitle} items={asStringList(missing)} />
      <ReqList title={redFlagsTitle} items={asStringList(redFlags)} />
    </div>
  );
}
