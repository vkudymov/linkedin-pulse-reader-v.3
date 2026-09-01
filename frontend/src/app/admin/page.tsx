import { redirect } from "next/navigation";

import { AppHeader } from "@/components/AppHeader";
import { AdminUsersTable } from "@/components/admin/AdminUsersTable";
import { createSupabaseServerClient } from "@/lib/supabase/server";

type AdminUserRow = {
  id: string;
  email: string | null;
  created_at: string | null;
  full_name: string | null;
  is_admin: boolean;
  is_blocked: boolean;
  blocked_at: string | null;
  post_search_run_count: number;
};

export default async function AdminPage() {
  const supabase = await createSupabaseServerClient();
  const { data } = await supabase.auth.getUser();
  if (!data.user) redirect("/login");

  const profileResp = await supabase
    .from("user_admin_state")
    .select("is_admin,is_blocked")
    .eq("id", data.user.id)
    .maybeSingle();

  const isAdmin = Boolean(profileResp.data?.is_admin);
  const isBlocked = Boolean(profileResp.data?.is_blocked);
  if (!isAdmin) redirect("/posts");
  if (isBlocked) redirect("/login?blocked=1");

  let users: AdminUserRow[] = [];
  try {
    const { data: sessionData } = await supabase.auth.getSession();
    const accessToken = sessionData.session?.access_token ?? null;
    if (accessToken) {
      const baseUrl = (process.env.WORKER_API_URL || "http://127.0.0.1:8000")
        .trim()
        .replace(/\/+$/, "");
      const resp = await fetch(`${baseUrl}/v1/admin/users`, {
        method: "GET",
        cache: "no-store",
        headers: { authorization: `Bearer ${accessToken}` },
      });
      if (resp.ok) {
        users = (await resp.json()) as AdminUserRow[];
      }
    }
  } catch {
    users = [];
  }

  return (
    <div className="min-h-screen bg-background text-foreground">
      <AppHeader
        title="Администратор"
        subtitle={data.user.email ?? null}
        active="admin"
        isAdmin
      />

      <main className="mx-auto max-w-5xl px-6 py-6">
        <AdminUsersTable initialUsers={users} />
      </main>
    </div>
  );
}

