import "server-only";

const BASE = "http://127.0.0.1:8765";

export async function api<T>(path: string, method = "GET", body?: object): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
    cache: "no-store",
  });
  if (!response.ok) {
    let detail = `API returned ${response.status}`;
    let conflict: { kind: "candidate" | "source"; id: number } | undefined;
    try {
      const result = await response.json();
      detail = typeof result.detail === "string" ? result.detail : detail;
      const data = result.detail;
      if (path === "/candidates" && response.status === 409 && data &&
        (data.kind === "candidate" || data.kind === "source") && Number.isSafeInteger(data.id) && data.id > 0) {
        conflict = { kind: data.kind, id: data.id };
      }
    } catch { /* safe fallback */ }
    throw Object.assign(new Error(detail), conflict ? { conflict } : {});
  }
  return response.json() as Promise<T>;
}

export type Source = { id: number; name: string; url: string; language: string };
export type Incident = { id: number; state: string; title_en: string; title_ar: string; category: string; review?: Record<string, unknown>; [key: string]: unknown };
export type Evidence = { id: number; source_id: number; url: string; text: string; published_at: string };
export type FeedHealth = {
  status: "pending" | "healthy" | "not-modified" | "delayed";
  last_success_at: string | null;
  consecutive_failures: number;
  last_error_category: string | null;
};
export type FeedSource = {
  id: number;
  name: string;
  url: string;
  feed_url: string;
  language: "en" | "ar";
  enabled: boolean;
  poll_interval_minutes: number;
  health: FeedHealth;
};
export type FeedItemStatus = "new" | "promoted" | "attached" | "duplicate" | "quarantined";
export type FeedItem = {
  id: number;
  source_id: number;
  status: FeedItemStatus;
  headline: string | null;
  url?: string;
  text?: string;
  published_at?: string;
  collected_at: string;
  incident_id?: number | null;
  reason?: string;
};

export type IntakeItem = FeedItem & {
  platform: "rss" | "telegram";
  native_id?: string | null;
  edited_at?: string | null;
  deleted_at?: string | null;
};
export type TelegramStatus = { state: "not-configured" | "reauthentication-required" | "authenticated" | "expired" };
export type TelegramChannel = {
  id: number;
  name: string;
  username: string;
  language: "en" | "ar" | "mixed";
  enabled: boolean;
  media_enabled: boolean;
  status: string | null;
  last_success_at: string | null;
};

export type PublicTelegramRecord = {
  id: string;
  status: "active" | "corrected" | "withdrawn";
  channel: { name: string; username: string; language: "en" | "ar" | "mixed" };
  url: string;
  headline: { en: string; ar: string };
  publishedAt: string;
  approvedAt: string;
  revisions: Array<{
    revisedAt: string;
    action: "corrected" | "withdrawn";
    reason: { en: string; ar: string };
    previousHeadline?: { en: string; ar: string };
  }>;
};
export type TelegramPublicationPreview = { item_id: number; draft_hash: string; record: PublicTelegramRecord };
export type TelegramPublication = { id: number; public_id: string; status: PublicTelegramRecord["status"]; record: PublicTelegramRecord };

export type CandidateStatus = "pending" | "accepted" | "rejected";
export type CandidateChecks = {
  accessibility_checked: boolean;
  relevance_checked: boolean;
  identity_checked: boolean;
  provenance_checked: boolean;
  policy_checked: boolean;
};
export type CandidateReview = {
  id: number;
  candidate_id: number;
  decision: Exclude<CandidateStatus, "pending">;
  reason: string;
  checks: CandidateChecks;
  created_at: string;
};
export type Candidate = {
  id: number;
  platform: "web" | "telegram";
  canonical_url: string;
  name: string;
  language: "en" | "ar" | "mixed";
  suggestion_reason: string;
  status: CandidateStatus;
  created_at: string;
  updated_at: string;
};
