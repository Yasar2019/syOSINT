export type IncidentCategory =
  | "armed-conflict"
  | "political-security"
  | "humanitarian"
  | "infrastructure"
  | "border-crossing"
  | "disinformation";

export type ConfidenceLabel =
  | "unverified"
  | "developing"
  | "corroborated"
  | "verified"
  | "disputed"
  | "false";

export type IncidentStatus = "published" | "corrected" | "withdrawn";

export type LocalizedText = { en: string; ar: string };

export interface PublicSourceReference {
  id: string;
  label: LocalizedText;
  url: string;
  publishedAt: string;
}

export interface PublicCorrection {
  correctedAt: string;
  reason: LocalizedText;
  changedFields: string[];
}

export interface PublicIncident {
  id: string;
  status: IncidentStatus;
  categories: IncidentCategory[];
  confidence: ConfidenceLabel;
  occurredAt: string;
  updatedAt: string;
  location: LocalizedText & {
    latitude?: number;
    longitude?: number;
    precision: "country" | "governorate" | "district" | "withheld";
  };
  title: LocalizedText;
  summary: LocalizedText;
  uncertainty: LocalizedText;
  sourceCount: number;
  sources: PublicSourceReference[];
  corrections: PublicCorrection[];
}

export interface PublicDataset {
  schemaVersion: "1.0.0";
  generatedAt: string;
  synthetic: boolean;
  incidents: PublicIncident[];
}

export interface PublicNewsWireEntry {
  id: string;
  sourceId: string;
  sourceLabel: LocalizedText;
  language: "en" | "ar";
  headline: string;
  url: string;
  publishedAt: string;
  collectedAt: string;
}

export interface PublicNewsWire {
  schemaVersion: "1.0.0";
  generatedAt: string;
  lastSuccessfulRefreshAt: string;
  sources: { healthy: number; delayed: number };
  entries: PublicNewsWireEntry[];
}
