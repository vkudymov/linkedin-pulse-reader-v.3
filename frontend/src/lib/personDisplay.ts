const nameTrailRe = /\s*[•·]\s*(?:\d[\d\s]*(st|nd|rd)\+?|.+)$/i;
const ctaRe =
  /\b(установить контакт|отправить сообщение|написать сообщение|подписаться|connect|message|follow|following)\b/gi;
const degreeLeadRe = /^\s*\d[\d\s]*(st|nd|rd)?\+?\s*[•·]?\s*/i;
const currentRoleRe = /[\s•·|,-]*(?:current|текущая)\s*:\s*.+$/gi;

export function displayPersonName(raw: string | null | undefined): string | null {
  if (!raw?.trim()) return null;
  let text = raw.replace(/\s+/g, " ").trim();
  text = text.replace(nameTrailRe, "").trim();
  if (text.length > 80) text = `${text.slice(0, 77).trim()}…`;
  return text || null;
}

export function displayPersonHeadline(
  raw: string | null | undefined,
  opts?: { name?: string | null; location?: string | null },
): string | null {
  if (!raw?.trim()) return null;
  let text = raw.replace(/\s+/g, " ").trim();
  text = text.replace(ctaRe, "").trim();
  text = text.replace(currentRoleRe, "").trim();
  text = text.replace(degreeLeadRe, "").trim();

  const name = opts?.name?.trim();
  if (name && text.toLowerCase().startsWith(name.toLowerCase())) {
    text = text.slice(name.length).trim();
  }

  const location = opts?.location?.trim();
  if (location) {
    if (text.endsWith(location)) text = text.slice(0, -location.length).trim();
    if (text.includes(location)) text = text.split(location).join(" ").trim();
  }

  text = text.replace(/^[\s•·,-]+/, "").replace(/[\s•·,-]+$/, "").trim();
  if (text.length > 140) text = `${text.slice(0, 137).trim()}…`;
  return text || null;
}
