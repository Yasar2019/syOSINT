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
    try { const result = await response.json(); detail = typeof result.detail === "string" ? result.detail : detail; } catch { /* safe fallback */ }
    throw new Error(detail);
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
