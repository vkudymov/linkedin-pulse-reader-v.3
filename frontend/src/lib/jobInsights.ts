export type JobInsightKey =
  | "on_site"
  | "remote"
  | "hybrid"
  | "full_time"
  | "part_time"
  | "contract"
  | "temporary"
  | "internship"
  | "freelance";

export type JobInsightKind = "workplace" | "employment";

export type JobInsightChip = {
  key: JobInsightKey;
  kind: JobInsightKind;
};

const WORKPLACE: { key: JobInsightKey; re: RegExp }[] = [
  { key: "on_site", re: /on[\s-]?site|in[\s-]?office|работ\w*\s+в\s+офисе|\bв\s+офисе\b/i },
  { key: "remote", re: /\bremote\b|work\s+from\s+home|удал[её]нн|дистанцион/i },
  { key: "hybrid", re: /\bhybrid\b|гибрид/i },
];

const EMPLOYMENT: { key: JobInsightKey; re: RegExp }[] = [
  { key: "full_time", re: /full[\s-]?time|полный\s+рабочий\s+день|полная\s+занятость/i },
  { key: "part_time", re: /part[\s-]?time|неполн(?:ый|ая|ую)|частичн/i },
  { key: "internship", re: /internship|стажир/i },
  { key: "freelance", re: /freelance|фриланс/i },
  { key: "temporary", re: /temporary|временн/i },
  { key: "contract", re: /\bcontract\b|контракт/i },
];

const WORKPLACE_KEYS = new Set(WORKPLACE.map((x) => x.key));
const EMPLOYMENT_KEYS = new Set(EMPLOYMENT.map((x) => x.key));
const SPLIT_RE = /\s*[·•|]\s*/;
const CRITERIA_RE =
  /(?:employment type|тип занятости|workplace type|формат работы|тип работы)\s*[:\n]+\s*([^\n]+)/gi;

export function resolveJobInsights(input: {
  workplace_type?: string | null;
  employment_type?: string | null;
  insights?: string[] | null;
  location?: string | null;
  description?: string | null;
}): JobInsightChip[] {
  const workplace =
    asWorkplaceKey(input.workplace_type) ||
    firstMatch(collectCandidates(input), WORKPLACE);
  const employment =
    asEmploymentKey(input.employment_type) ||
    firstMatch(collectCandidates(input), EMPLOYMENT);

  const chips: JobInsightChip[] = [];
  if (workplace) chips.push({ key: workplace, kind: "workplace" });
  if (employment) chips.push({ key: employment, kind: "employment" });
  return chips;
}

export function stripInsightPhrases(location: string | null | undefined): string | null {
  if (!location) return null;
  const parts = location
    .split(SPLIT_RE)
    .map((p) => p.trim())
    .filter(Boolean)
    .filter((p) => !matchKey(p, WORKPLACE) && !matchKey(p, EMPLOYMENT))
    .map((p) => p.replace(/\(\s*(on[\s-]?site|remote|hybrid|в офисе|удал[её]нно|гибрид)\s*\)/gi, "").trim())
    .filter(Boolean);
  const cleaned = parts.join(" · ").replace(/\s{2,}/g, " ").trim();
  return cleaned || null;
}

function collectCandidates(input: {
  insights?: string[] | null;
  location?: string | null;
  description?: string | null;
}): string[] {
  const out: string[] = [];
  for (const raw of input.insights || []) out.push(...splitSegments(raw));
  out.push(...splitSegments(input.location));
  if (input.description) {
    for (const match of input.description.matchAll(CRITERIA_RE)) {
      out.push(...splitSegments(match[1]));
    }
    out.push(...splitSegments(input.description.slice(0, 800)));
    if (input.description.length > 800) {
      out.push(...splitSegments(input.description.slice(-2000)));
    }
  }
  return out.filter((s) => s.length >= 3 && s.length <= 64);
}

function splitSegments(text: string | null | undefined): string[] {
  if (!text) return [];
  return text
    .split(SPLIT_RE)
    .map((p) => p.replace(/\s+/g, " ").trim())
    .filter(Boolean);
}

function asWorkplaceKey(value: string | null | undefined): JobInsightKey | null {
  if (!value) return null;
  if (WORKPLACE_KEYS.has(value as JobInsightKey)) return value as JobInsightKey;
  return matchKey(value, WORKPLACE);
}

function asEmploymentKey(value: string | null | undefined): JobInsightKey | null {
  if (!value) return null;
  if (EMPLOYMENT_KEYS.has(value as JobInsightKey)) return value as JobInsightKey;
  return matchKey(value, EMPLOYMENT);
}

function firstMatch(
  texts: string[],
  table: { key: JobInsightKey; re: RegExp }[],
): JobInsightKey | null {
  for (const text of texts) {
    const key = matchKey(text, table);
    if (key) return key;
  }
  return null;
}

function matchKey(
  text: string,
  table: { key: JobInsightKey; re: RegExp }[],
): JobInsightKey | null {
  for (const row of table) {
    if (row.re.test(text)) return row.key;
  }
  return null;
}
