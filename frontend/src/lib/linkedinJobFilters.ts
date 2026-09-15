export type DatePostedFilter = "any" | "day" | "week" | "month";
export type ExperienceFilter =
  | "any"
  | "internship"
  | "entry"
  | "associate"
  | "mid_senior"
  | "director"
  | "executive";
export type EmploymentFilter =
  | "any"
  | "full_time"
  | "part_time"
  | "contract"
  | "temporary"
  | "internship";

export type LinkedInJobFilters = {
  date_posted: DatePostedFilter;
  remote: boolean;
  easy_apply: boolean;
  experience: ExperienceFilter;
  employment: EmploymentFilter;
  company: string;
};

export const DEFAULT_LINKEDIN_JOB_FILTERS: LinkedInJobFilters = {
  date_posted: "week",
  remote: false,
  easy_apply: false,
  experience: "any",
  employment: "full_time",
  company: "",
};

const DATE_POSTED = new Set<DatePostedFilter>(["any", "day", "week", "month"]);
const EXPERIENCE = new Set<ExperienceFilter>([
  "any",
  "internship",
  "entry",
  "associate",
  "mid_senior",
  "director",
  "executive",
]);
const EMPLOYMENT = new Set<EmploymentFilter>([
  "any",
  "full_time",
  "part_time",
  "contract",
  "temporary",
  "internship",
]);

export function normalizeLinkedInJobFilters(raw: unknown): LinkedInJobFilters {
  const src = raw && typeof raw === "object" ? (raw as Record<string, unknown>) : {};
  const datePosted = src.date_posted;
  const experience = src.experience;
  const employment = src.employment;
  return {
    date_posted: DATE_POSTED.has(datePosted as DatePostedFilter)
      ? (datePosted as DatePostedFilter)
      : DEFAULT_LINKEDIN_JOB_FILTERS.date_posted,
    remote: src.remote === true,
    easy_apply: src.easy_apply === true,
    experience: EXPERIENCE.has(experience as ExperienceFilter)
      ? (experience as ExperienceFilter)
      : DEFAULT_LINKEDIN_JOB_FILTERS.experience,
    employment: EMPLOYMENT.has(employment as EmploymentFilter)
      ? (employment as EmploymentFilter)
      : DEFAULT_LINKEDIN_JOB_FILTERS.employment,
    company: typeof src.company === "string" ? src.company.trim() : "",
  };
}
