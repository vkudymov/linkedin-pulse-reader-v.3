-- Store per-user LLM prompts in user_profiles (1:1 with auth.users).
-- search_prompt is required at runtime by the worker, but remains nullable in DB.

alter table public.user_profiles
  add column if not exists search_prompt text,
  add column if not exists comment_prompt text;

