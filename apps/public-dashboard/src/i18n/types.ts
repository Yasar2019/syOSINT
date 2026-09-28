import type { ConfidenceLabel, IncidentCategory, IncidentStatus } from "@syosint/schemas";

export type Locale = "en" | "ar";

export interface Dictionary {
  navigation: {
    methodology: string;
    repository: string;
  };
  brand: {
    eyebrow: string;
    title: string;
    subtitle: string;
    lastUpdated: string;
  };
  demo: {
    title: string;
    body: string;
  };
  telegramWire: {
    reportingMode: string;
    dateFilter: string;
    modes: { all: string; rss: string; telegram: string };
    title: string;
    disclosure: string;
    updated: string;
    window: string;
    empty: string;
    withdrawn: string;
    history: string;
    previous: string;
    status: { active: string; corrected: string; withdrawn: string };
  };
  newsWire: {
    title: string;
    disclosure: string;
    refreshed: string;
    sourceFilter: string;
    allSources: string;
    languageFilter: string;
    allLanguages: string;
    english: string;
    arabic: string;
    configured: string;
    healthy: string;
    delayedCount: string;
    headline: string;
    headlines: string;
    sourceDelayed: string;
    sourceEmpty: string;
    noRecentHeadlines: string;
    showMore: string;
    empty: string;
    emptyDelayed: string;
    delayed: string;
    stale: string;
    externalLinkContext: string;
  };
  filters: {
    title: string;
    searchLabel: string;
    searchPlaceholder: string;
    categories: string;
    confidence: string;
    reset: string;
    results: string;
  };
  categories: Record<IncidentCategory, string>;
  confidence: Record<ConfidenceLabel, string>;
  status: Record<IncidentStatus, string>;
  summary: {
    total: string;
    verified: string;
    needsAttention: string;
  };
  feed: {
    title: string;
    empty: string;
    viewDetails: string;
  };
  detail: {
    title: string;
    close: string;
    occurred: string;
    updated: string;
    sources: string;
    uncertainty: string;
    corrections: string;
    noCorrections: string;
  };
  map: {
    title: string;
    description: string;
    noLocation: string;
  };
  timeline: {
    title: string;
  };
  methodology: {
    title: string;
    intro: string;
  };
  accessibility: {
    skipToContent: string;
    openIncident: string;
    externalLink: string;
  };
}
