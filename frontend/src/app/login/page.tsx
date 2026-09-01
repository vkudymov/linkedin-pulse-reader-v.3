import { AuthForm } from "@/components/AuthForm";

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ blocked?: string }>;
}) {
  const { blocked } = await searchParams;
  return (
    <div className="space-y-3">
      {blocked ? (
        <div className="mx-auto max-w-md px-6 pt-10 text-sm text-destructive">
          Пользователь заблокирован.
        </div>
      ) : null}
      <AuthForm variant="login" />
    </div>
  );
}

