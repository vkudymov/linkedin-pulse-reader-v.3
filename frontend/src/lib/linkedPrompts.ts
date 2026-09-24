export const LINKED_PROMPT_SELECT =
  "filter_prompt_id,search_prompt_id,comment_prompt_id," +
  "filter_prompt:prompts!searches_filter_prompt_id_fkey(id,role,title,body)," +
  "search_prompt:prompts!searches_search_prompt_id_fkey(id,role,title,body)," +
  "comment_prompt:prompts!searches_comment_prompt_id_fkey(id,role,title,body)";

function promptBody(value: unknown): string {
  if (value && typeof value === "object" && typeof (value as { body?: unknown }).body === "string") {
    return String((value as { body: string }).body || "");
  }
  return "";
}

export function attachLinkedPrompts(row: Record<string, unknown>): Record<string, unknown> {
  const out = { ...row };
  out.filter_prompt = promptBody(row.filter_prompt);
  out.search_prompt = promptBody(row.search_prompt);
  const comment = promptBody(row.comment_prompt);
  out.comment_prompt = comment || null;
  return out;
}
