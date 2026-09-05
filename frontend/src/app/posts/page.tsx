import { cookies } from "next/headers";
import { redirect } from "next/navigation";

export default async function PostsPage() {
  const cookieStore = await cookies();
  const localeCookie = cookieStore.get("NEXT_LOCALE")?.value;
  const locale = localeCookie === "en" ? "en" : "ru";
  redirect(`/${locale}/posts`);
}

