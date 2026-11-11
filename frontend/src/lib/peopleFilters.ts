export type NetworkCode = "F" | "S" | "O";

export type PeopleFilters = {
  network: NetworkCode[];
  locations: string[];
  current_company: string[];
  past_company: string[];
  school: string[];
  industry: string[];
  profile_language: string;
  keywords: string;
};

export const DEFAULT_PEOPLE_FILTERS: PeopleFilters = {
  network: [],
  locations: [],
  current_company: [],
  past_company: [],
  school: [],
  industry: [],
  profile_language: "",
  keywords: "",
};

export const PEOPLE_PROFILE_LANGUAGES = [
  "en",
  "ru",
  "de",
  "fr",
  "es",
  "it",
  "pt",
  "nl",
  "pl",
  "tr",
  "zh",
  "ja",
  "ko",
  "ar",
] as const;

export const PEOPLE_INDUSTRIES: { id: string; label: string }[] = [
  { id: "4", label: "Software Development" },
  { id: "6", label: "Technology, Information and Internet" },
  { id: "96", label: "IT Services and IT Consulting" },
  { id: "3", label: "Computer Hardware" },
  { id: "8", label: "Computer Networking Products" },
  { id: "7", label: "Semiconductor Manufacturing" },
  { id: "24", label: "Telecommunications" },
  { id: "118", label: "Research Services" },
  { id: "11", label: "Business Consulting and Services" },
  { id: "43", label: "Financial Services" },
  { id: "41", label: "Banking" },
  { id: "80", label: "Advertising Services" },
  { id: "137", label: "Human Resources Services" },
  { id: "14", label: "Higher Education" },
  { id: "25", label: "Manufacturing" },
  { id: "15", label: "Pharmaceutical Manufacturing" },
  { id: "186", label: "Information Services" },
  { id: "109", label: "Computer Games" },
];

const NETWORK = new Set<NetworkCode>(["F", "S", "O"]);
const LANGUAGES = new Set<string>(PEOPLE_PROFILE_LANGUAGES);

function asList(value: unknown): string[] {
  if (typeof value === "string") {
    const s = value.trim();
    return s ? [s] : [];
  }
  if (!Array.isArray(value)) return [];
  return value
    .map((item) => (typeof item === "string" ? item.trim() : typeof item === "number" ? String(item) : ""))
    .filter(Boolean);
}

export function normalizePeopleFilters(raw: unknown): PeopleFilters {
  const src = raw && typeof raw === "object" ? (raw as Record<string, unknown>) : {};
  const network = asList(src.network)
    .map((c) => c.toUpperCase())
    .filter((c): c is NetworkCode => NETWORK.has(c as NetworkCode));
  const lang = typeof src.profile_language === "string" ? src.profile_language.trim().toLowerCase() : "";
  return {
    network,
    locations: asList(src.locations),
    current_company: asList(src.current_company),
    past_company: asList(src.past_company),
    school: asList(src.school),
    industry: asList(src.industry),
    profile_language: LANGUAGES.has(lang) ? lang : "",
    keywords: typeof src.keywords === "string" ? src.keywords.trim() : "",
  };
}

export function peopleFiltersActiveCount(filters: PeopleFilters): number {
  return (
    filters.network.length +
    filters.locations.length +
    filters.current_company.length +
    filters.past_company.length +
    filters.school.length +
    filters.industry.length +
    (filters.profile_language ? 1 : 0) +
    (filters.keywords ? 1 : 0)
  );
}
