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
