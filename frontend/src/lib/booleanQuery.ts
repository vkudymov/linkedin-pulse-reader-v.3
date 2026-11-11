export type BooleanQueryResult = {
  query: string;
  warnings: string[];
  errors: string[];
  ok: boolean;
};

const SMART_QUOTES: Record<string, string> = {
  "\u201c": '"',
  "\u201d": '"',
  "\u201e": '"',
  "\u00ab": '"',
  "\u00bb": '"',
  "\u2018": "'",
  "\u2019": "'",
};

const PLUS_MINUS_RE = /(?<![A-Za-z0-9])[+\-](?=\S)/;

function replaceSmartQuotes(text: string): string {
  let out = text;
  for (const [src, dst] of Object.entries(SMART_QUOTES)) {
    out = out.split(src).join(dst);
  }
  return out;
}

function splitQuoted(text: string): Array<[string, boolean]> {
  const parts: Array<[string, boolean]> = [];
  let buf = "";
  let inQuote = false;
  for (const ch of text) {
    if (ch === '"') {
      if (inQuote) {
        buf += ch;
        parts.push([buf, true]);
        buf = "";
        inQuote = false;
      } else {
        if (buf) parts.push([buf, false]);
        buf = ch;
        inQuote = true;
      }
    } else {
      buf += ch;
    }
  }
  if (buf) parts.push([buf, inQuote]);
  return parts;
}

function uppercaseOperators(text: string): string {
  return splitQuoted(text)
    .map(([chunk, quoted]) => (quoted ? chunk : chunk.replace(/\b(and|or|not)\b/g, (_, op: string) => op.toUpperCase())))
    .join("");
}

function balanced(text: string): { quotesOk: boolean; parensOk: boolean } {
  let inQuote = false;
  let depth = 0;
  for (const ch of text) {
    if (ch === '"') {
      inQuote = !inQuote;
      continue;
    }
    if (inQuote) continue;
    if (ch === "(") depth += 1;
    else if (ch === ")") {
      depth -= 1;
      if (depth < 0) return { quotesOk: !inQuote, parensOk: false };
    }
  }
  return { quotesOk: !inQuote, parensOk: depth === 0 };
}

function tokensOutsideQuotes(text: string): string[] {
  const tokens: string[] = [];
  for (const [chunk, quoted] of splitQuoted(text)) {
    if (quoted) {
      tokens.push(chunk);
      continue;
    }
    const found = chunk.match(/\(|\)|\bAND\b|\bOR\b|\bNOT\b|[^\s()]+/g);
    if (found) tokens.push(...found);
  }
  return tokens;
}

export function validateBooleanQuery(text: string): string[] {
  const errors: string[] = [];
  const { quotesOk, parensOk } = balanced(text);
  if (!quotesOk) errors.push("unbalanced quotes");
  if (!parensOk) errors.push("unbalanced parentheses");
  const tokens = tokensOutsideQuotes(text);
  if (tokens.length) {
    const first = tokens[0];
    const last = tokens[tokens.length - 1];
    if (first === "AND" || first === "OR") errors.push("query cannot start with AND/OR");
    if (last === "AND" || last === "OR" || last === "NOT") errors.push("query cannot end with AND/OR/NOT");
  }
  return errors;
}

export function normalizeBooleanQuery(raw: string): BooleanQueryResult {
  let text = replaceSmartQuotes(raw || "").trim();
  const warnings: string[] = [];
  if (PLUS_MINUS_RE.test(text)) {
    warnings.push("LinkedIn does not support + or -; use AND / NOT instead");
  }
  text = uppercaseOperators(text);
  text = text.replace(/\s+/g, " ").trim();
  const errors = validateBooleanQuery(text);
  return { query: text, warnings, errors, ok: errors.length === 0 };
}
