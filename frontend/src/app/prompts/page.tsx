import { redirect } from "next/navigation";

import { AppHeader } from "@/components/AppHeader";
import { PostSearchRunner } from "@/components/PostSearchRunner";
import { PromptForm } from "@/components/PromptForm";
import { requireNotBlocked } from "@/lib/auth/blocked";
import { createSupabaseServerClient } from "@/lib/supabase/server";
import type { UserProfileRow } from "@/types/database";

export default async function PromptsPage() {
  const supabase = await createSupabaseServerClient();
  const { data } = await supabase.auth.getUser();
  if (!data.user) redirect("/login");
  const isAdmin = await requireNotBlocked(supabase, data.user.id);

  const profileResp = await supabase
    .from("user_profiles_view")
    .select("*")
    .eq("id", data.user.id)
    .maybeSingle();

  const profile = (profileResp.data || null) as UserProfileRow | null;

  return (
    <div className="min-h-screen bg-background text-foreground">
      <AppHeader
        title="Промпты"
        subtitle={data.user.email ?? null}
        active="prompts"
        isAdmin={isAdmin}
      />

      <main className="mx-auto max-w-3xl px-6 py-6">
        <div className="overflow-hidden rounded-2xl border border-border bg-card">
          <div className="border-b border-border px-6 py-5">
            <div className="space-y-1">
              <h2 className="text-lg font-semibold tracking-tight">Настройки промптов</h2>
              <p className="max-w-xl text-sm leading-6 text-muted-foreground">
                Отредактируйте промпты и сохраните. После этого можно запустить поиск постов.
              </p>
            </div>
          </div>

          <div className="p-6">
            <PromptForm initialProfile={profile} />
          </div>
        </div>

        <div className="mt-6 overflow-hidden rounded-2xl border border-border bg-card">
          <div className="border-b border-border px-6 py-5">
            <div className="space-y-1">
              <h2 className="text-lg font-semibold tracking-tight">Запуск поиска</h2>
              <p className="max-w-xl text-sm leading-6 text-muted-foreground">
                После завершения поиска лента постов обновится автоматически.
              </p>
            </div>
          </div>

          <div className="p-6">
            <PostSearchRunner />
          </div>
        </div>
      </main>
    </div>
  );
}

