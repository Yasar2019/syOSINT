import type { Dictionary } from "./types";

export const en = {
  navigation: {
    methodology: "Methodology",
    repository: "Source code",
  },
  brand: {
    eyebrow: "Open-source situation monitor",
    title: "Syria Situation Desk",
    subtitle: "Human-reviewed public reporting with visible uncertainty.",
    lastUpdated: "Dataset updated",
  },
  demo: {
    title: "Demonstration data only",
    body: "Every incident shown in this milestone is fictional and does not represent a real event or person.",
  },
  filters: {
    title: "Filter incidents",
    searchLabel: "Search incidents",
    searchPlaceholder: "Search titles, summaries, or locations",
    categories: "Categories",
    confidence: "Confidence",
    reset: "Reset filters",
    results: "incidents visible",
  },
  categories: {
    "armed-conflict": "Armed conflict",
    "political-security": "Political and security",
    humanitarian: "Humanitarian",
    infrastructure: "Infrastructure",
    "border-crossing": "Border and crossing",
    disinformation: "Disinformation",
  },
  confidence: {
    unverified: "Unverified",
    developing: "Developing",
    corroborated: "Corroborated",
    verified: "Verified",
    disputed: "Disputed",
    false: "False",
  },
  status: {
    published: "Published",
    corrected: "Corrected",
    withdrawn: "Withdrawn",
  },
  summary: {
    total: "Visible incidents",
    verified: "Corroborated or verified",
    needsAttention: "Disputed or unverified",
  },
  feed: {
    title: "Incident feed",
    empty: "No incidents match the active filters.",
    viewDetails: "View details",
  },
  detail: {
    title: "Incident detail",
    close: "Close details",
    occurred: "Occurred",
    updated: "Last reviewed",
    sources: "Public references",
    uncertainty: "What remains uncertain",
    corrections: "Correction history",
    noCorrections: "No corrections recorded.",
  },
  map: {
    title: "Syria situation map",
    description: "Generalized demonstration locations; no live tactical positions.",
    noLocation: "Location withheld",
  },
  timeline: {
    title: "Activity timeline",
  },
  methodology: {
    title: "Methodology",
    intro: "How syOSINT separates collection, verification, safety review, and publication.",
  },
  accessibility: {
    skipToContent: "Skip to content",
    openIncident: "Open incident",
    externalLink: "opens in a new tab",
  },
} satisfies Dictionary;
