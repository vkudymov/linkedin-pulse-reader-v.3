import "server-only";

import { appendFile, mkdir } from "node:fs/promises";
import path from "node:path";

type LogLevel = "info" | "warn" | "error";

type LogEntry = {
  level: LogLevel;
  scope: string;
  message: string;
  where?: string;
  hint?: string;
  meta?: Record<string, unknown>;
};

function sanitizeMeta(meta: Record<string, unknown> | undefined) {
  if (!meta) return undefined;
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(meta)) {
    if (k.toLowerCase().includes("key") || k.toLowerCase().includes("token")) continue;
    out[k] = v;
  }
  return out;
}

function formatLine(e: LogEntry) {
  const meta = sanitizeMeta(e.meta);
  const parts = [
    `ts=${new Date().toISOString()}`,
    `level=${e.level.toUpperCase()}`,
    `scope=${JSON.stringify(e.scope)}`,
    `message=${JSON.stringify(e.message)}`,
  ];
  if (e.where) parts.push(`where=${JSON.stringify(e.where)}`);
  if (e.hint) parts.push(`hint=${JSON.stringify(e.hint)}`);
  if (meta && Object.keys(meta).length) parts.push(`meta=${JSON.stringify(meta)}`);
  return parts.join(" ");
}

function resolveLogDir() {
  const cwd = process.cwd();
  if (cwd.endsWith(`${path.sep}frontend`) || cwd === "frontend") return path.join(cwd, "log");
  return path.join(cwd, "frontend", "log");
}

export async function writeLog(entry: LogEntry) {
  try {
    const logDir = resolveLogDir();
    await mkdir(logDir, { recursive: true });
    const date = new Date().toISOString().slice(0, 10);
    const file = path.join(logDir, `app-${date}.log`);
    await appendFile(file, `${formatLine(entry)}\n`, { encoding: "utf-8" });
  } catch {
    // Best-effort only.
  }
}

