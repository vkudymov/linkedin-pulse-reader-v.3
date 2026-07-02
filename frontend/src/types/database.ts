export type LinkedInAccountRow = {
  id: string;
  label: string | null;
  li_profile_url: string | null;
  created_at: string;
};

export type FeedPostRow = {
  id: string;
  linkedin_account_id: string;
  source_key: string;
  urn: string | null;
  post_url: string;
  author_json: {
    name?: string | null;
    headline?: string | null;
    profile_url?: string | null;
    urn?: string | null;
    [k: string]: unknown;
  } | null;
  content: string | null;
  published_at_text: string | null;
  reactions_count: number | null;
  comments_count: number | null;
  media_urls: string[];
  raw_extra: Record<string, unknown> | null;
  is_relevant: boolean | null;
  comment_text: string | null;
  analysis_error: string | null;
  analysis_payload: Record<string, unknown> | null;
  fetched_at: string;
  analyzed_at: string | null;
};

