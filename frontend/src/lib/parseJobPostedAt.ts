const MINUTE_MS = 60_000;
const HOUR_MS = 3_600_000;
const DAY_MS = 86_400_000;

function unitToMs(unit: string): number | null {
  const u = unit.toLowerCase();
  if (/^(minutes?|mins?|минут[аыу]?)$/.test(u)) return MINUTE_MS;
  if (/^(hours?|hrs?|час(?:а|ов)?)$/.test(u)) return HOUR_MS;
  if (/^(days?|дн(?:я|ей|ень)?)$/.test(u)) return DAY_MS;
  if (/^(weeks?|недел[яиью]?)$/.test(u)) return 7 * DAY_MS;
  if (/^(months?|месяц(?:а|ев)?)$/.test(u)) return 30 * DAY_MS;
  if (/^(years?|год(?:а|ов)?|лет)$/.test(u)) return 365 * DAY_MS;
  return null;
}

export function parseJobPostedAtMs(
  text: string | null | undefined,
  now = Date.now(),
): number | null {
  if (!text) return null;
  const raw = text.trim();
  if (!raw) return null;

  const asDate = Date.parse(raw);
  if (!Number.isNaN(asDate)) return asDate;

  const lower = raw.toLowerCase();
  if (/\b(just now|сегодня|today|только что)\b/.test(lower)) return now;
  if (/\b(yesterday|вчера)\b/.test(lower)) return now - DAY_MS;

  const match = lower.match(
    /(\d+)\s*(minutes?|mins?|минут[аыу]?|hours?|hrs?|час(?:а|ов)?|days?|дн(?:я|ей|ень)?|weeks?|недел[яиью]?|months?|месяц(?:а|ев)?|years?|год(?:а|ов)?|лет)/i,
  );
  if (!match) return null;
  const amount = Number(match[1]);
  const unitMs = unitToMs(match[2] || "");
  if (!Number.isFinite(amount) || amount < 0 || unitMs == null) return null;
  return now - amount * unitMs;
}
