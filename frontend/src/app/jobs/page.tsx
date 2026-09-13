import { cookies } from "next/headers";
import { redirect } from "next/navigation";

export default async function JobsRedirectPage() {
  const cookieStore = await cookies();
  const raw = cookieStore.get("NEXT_LOCALE")?.value;
  const locale = raw === "en" ? "en" : "ru";
  redirect(`/${locale}/jobs`);
}

