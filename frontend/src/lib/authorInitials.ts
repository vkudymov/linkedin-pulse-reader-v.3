/** Fixed locale so Node SSR and browser produce the same uppercase initials. */
const INITIALS_LOCALE = "en-US";

function firstChar(s: string): string {
  const normalized = s.normalize("NFC").trim();
  if (!normalized) return "";
  return Array.from(normalized)[0] ?? "";
}

export function authorInitials(name: string | null | undefined): string {
  if (!name?.trim()) return "?";
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";

  const upper = (s: string) => s.toLocaleUpperCase(INITIALS_LOCALE);

  if (parts.length === 1) {
    const chars = Array.from(parts[0].normalize("NFC"));
    const initials = upper(chars.slice(0, 2).join(""));
    return initials || "?";
  }

  const a = firstChar(parts[0]);
  const b = firstChar(parts[parts.length - 1]!);
  const combined = upper(a + b);
  return combined || "?";
}
