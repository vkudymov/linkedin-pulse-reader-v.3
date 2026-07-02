import { log } from "@/lib/log/logger";
import { writeLog } from "@/lib/log/serverFile";

type Body = {
  level: "error" | "warn";
  scope: string;
  message: string;
  where?: string;
};

function isBody(v: unknown): v is Body {
  if (!v || typeof v !== "object") return false;
  const o = v as Record<string, unknown>;
  if (o.level !== "error" && o.level !== "warn") return false;
  if (typeof o.scope !== "string" || !o.scope.trim()) return false;
  if (typeof o.message !== "string" || !o.message.trim()) return false;
  if (o.where != null && typeof o.where !== "string") return false;
  return true;
}

export async function POST(request: Request) {
  let json: unknown = null;
  try {
    json = await request.json();
  } catch {
    return new Response("invalid json", { status: 400 });
  }

  if (!isBody(json)) return new Response("invalid body", { status: 400 });
  const body = json;

  const message = body.message.slice(0, 400);
  const scope = body.scope.slice(0, 60);
  const where = body.where?.slice(0, 120);

  if (body.level === "warn") {
    log.warn(scope, message, { where });
    await writeLog({ level: "warn", scope, message, where });
  } else {
    log.error(scope, message, { where });
    await writeLog({ level: "error", scope, message, where });
  }

  return new Response("ok", { status: 200 });
}

