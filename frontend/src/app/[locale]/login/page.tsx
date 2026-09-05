import { AuthForm } from "@/components/AuthForm";
import { getTranslations } from "next-intl/server";

export default async function LoginPage({
  params,
  searchParams,
}: {
  params: Promise<{ locale: string }>;
  searchParams: Promise<{ blocked?: string }>;
}) {
  // Keep params for server render stability (even if unused now).
  await params;
  const t = await getTranslations("auth.errors");
  const { blocked } = await searchParams;

  return (
    <div className="space-y-3">
      {blocked ? (
        <div className="mx-auto max-w-md px-6 pt-10 text-sm text-destructive">
          {t("blockedUser")}
        </div>
      ) : null}
      <AuthForm variant="login" />
    </div>
  );
}

