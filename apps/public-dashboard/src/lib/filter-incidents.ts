import type {
  ConfidenceLabel,
  IncidentCategory,
  PublicIncident,
} from "@syosint/schemas";

export interface DashboardFilters {
  categories: IncidentCategory[];
  confidence: ConfidenceLabel[];
  search: string;
}

export const EMPTY_FILTERS: DashboardFilters = {
  categories: [],
  confidence: [],
  search: "",
};

const confidenceLabels: ConfidenceLabel[] = [
  "unverified",
  "developing",
  "corroborated",
  "verified",
  "disputed",
  "false",
];

export function filterIncidents(
  incidents: PublicIncident[],
  filters: DashboardFilters,
): PublicIncident[] {
  const normalizedSearch = filters.search.trim().toLocaleLowerCase();

  return incidents
    .filter((incident) => {
      const matchesCategory =
        filters.categories.length === 0 ||
        filters.categories.some((category) => incident.categories.includes(category));
      const matchesConfidence =
        filters.confidence.length === 0 || filters.confidence.includes(incident.confidence);
      const searchableText = [
        incident.title.en,
        incident.title.ar,
        incident.summary.en,
        incident.summary.ar,
        incident.location.en,
        incident.location.ar,
      ]
        .join(" ")
        .toLocaleLowerCase();
      const matchesSearch =
        normalizedSearch.length === 0 || searchableText.includes(normalizedSearch);

      return matchesCategory && matchesConfidence && matchesSearch;
    })
    .toSorted((left, right) => {
      const byTime = Date.parse(right.occurredAt) - Date.parse(left.occurredAt);
      return byTime !== 0 ? byTime : left.id.localeCompare(right.id);
    });
}

export function countByConfidence(
  incidents: PublicIncident[],
): Record<ConfidenceLabel, number> {
  const counts = Object.fromEntries(
    confidenceLabels.map((label) => [label, 0]),
  ) as Record<ConfidenceLabel, number>;

  for (const incident of incidents) {
    counts[incident.confidence] += 1;
  }

  return counts;
}
