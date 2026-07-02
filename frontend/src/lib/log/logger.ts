type LogLevel = "info" | "warn" | "error";

type LogEntry = {
  level: LogLevel;
  scope: string;
  message: string;
  where?: string;
  hint?: string;
  meta?: Record<string, unknown>;
};

function short(level: LogLevel, scope: string, message: string) {
  const tag = level.toUpperCase();
  return `[${tag}] ${scope} ${message}`;
}

function sanitizeMeta(meta: Record<string, unknown> | undefined) {
  if (!meta) return undefined;
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(meta)) {
    if (k.toLowerCase().includes("key") || k.toLowerCase().includes("token")) continue;
    out[k] = v;
  }
  return out;
}

export const log = {
  info(scope: string, message: string, extra: Omit<LogEntry, "level" | "scope" | "message"> = {}) {
    console.log(short("info", scope, message));
    void sanitizeMeta(extra.meta);
  },
  warn(scope: string, message: string, extra: Omit<LogEntry, "level" | "scope" | "message"> = {}) {
    console.warn(short("warn", scope, message));
    void sanitizeMeta(extra.meta);
  },
  error(scope: string, message: string, extra: Omit<LogEntry, "level" | "scope" | "message"> = {}) {
    console.error(short("error", scope, message));
    void sanitizeMeta(extra.meta);
  },
};

