import { cookies } from "next/headers";
import { redirect } from "next/navigation";

function querySuffix(searchParams: Record<string, string | string[] | undefined>): string {
  const qs = new URLSearchParams();
  for (const [key, value] of Object.entries(searchParams)) {
    if (typeof value === "string") qs.set(key, value);
    else if (Array.isArray(value)) {
      for (const entry of value) qs.append(key, entry);
    }
  }
  const raw = qs.toString();
  return raw ? `?${raw}` : "";
}

export default async function SearchesPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const cookieStore = await cookies();
  const localeCookie = cookieStore.get("NEXT_LOCALE")?.value;
  const locale = localeCookie === "en" ? "en" : "ru";
  const sp = await searchParams;
  redirect(`/${locale}/searches${querySuffix(sp)}`);
}
