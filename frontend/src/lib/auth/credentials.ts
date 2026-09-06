export type AuthErrorCode =
  | "auth_failed"
  | "invalid_credentials"
  | "network"
  | "blocked";

export function parseEmailPassword(body: unknown): { email: string; password: string } | null {
  if (!body || typeof body !== "object") return null;
  const email = "email" in body && typeof body.email === "string" ? body.email.trim() : "";
  const password = "password" in body && typeof body.password === "string" ? body.password : "";
  if (!email || !password) return null;
  return { email, password };
}

export function authErrorCode(error: { message?: string; code?: string } | unknown): AuthErrorCode {
  const message =
    error && typeof error === "object" && "message" in error && typeof error.message === "string"
      ? error.message
      : "";
  const code =
    error && typeof error === "object" && "code" in error && typeof error.code === "string"
      ? error.code
      : "";

  if (/failed to fetch|fetch failed|network/i.test(message) || code === "network") {
    return "network";
  }
  if (
    /invalid login credentials/i.test(message) ||
    code === "invalid_credentials" ||
    code === "invalid_grant"
  ) {
    return "invalid_credentials";
  }
  return "auth_failed";
}
