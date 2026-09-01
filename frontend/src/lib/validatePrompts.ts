import { COMMENT_REQUIRED_MARKERS, SEARCH_REQUIRED_MARKER } from "@/lib/defaultPrompts";

function missingMarkers(value: string, markers: readonly string[]) {
  const v = value || "";
  return markers.filter((m) => !v.includes(m));
}

export type PromptsPayload = {
  search_prompt: string;
  comment_prompt: string | null;
};

export function validatePromptPayload(input: {
  search_prompt?: unknown;
  comment_prompt?: unknown;
}): { ok: true; value: PromptsPayload } | { ok: false; error: string } {
  const rawSearch = typeof input.search_prompt === "string" ? input.search_prompt : "";
  const rawComment = typeof input.comment_prompt === "string" ? input.comment_prompt : "";

  const search_prompt = rawSearch.trim();
  const comment_prompt_trimmed = rawComment.trim();
  const comment_prompt = comment_prompt_trimmed || null;

  if (!search_prompt) {
    return { ok: false, error: "Промпт поиска обязателен." };
  }
  if (!search_prompt.includes(SEARCH_REQUIRED_MARKER)) {
    return {
      ok: false,
      error: `Промпт поиска должен содержать маркер ${SEARCH_REQUIRED_MARKER}.`,
    };
  }
  if (comment_prompt) {
    const missing = missingMarkers(comment_prompt, [...COMMENT_REQUIRED_MARKERS]);
    if (missing.length > 0) {
      return {
        ok: false,
        error: `Промпт комментария должен содержать маркеры: ${missing.join(", ")}.`,
      };
    }
  }

  return { ok: true, value: { search_prompt, comment_prompt } };
}

export function getPromptIssues(value: { search_prompt: string; comment_prompt: string }) {
  const searchMissing = missingMarkers(value.search_prompt, [SEARCH_REQUIRED_MARKER]);
  const trimmedComment = value.comment_prompt.trim();
  const commentMissing = trimmedComment
    ? missingMarkers(trimmedComment, [...COMMENT_REQUIRED_MARKERS])
    : [];
  return {
    isSearchEmpty: !value.search_prompt.trim(),
    searchMissing,
    commentMissing,
  };
}

