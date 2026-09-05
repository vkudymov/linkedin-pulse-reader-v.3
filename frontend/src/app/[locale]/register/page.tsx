import { AuthForm } from "@/components/AuthForm";

export default async function RegisterPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  // Keep params for server render stability (even if unused now).
  await params;
  return <AuthForm variant="register" />;
}

