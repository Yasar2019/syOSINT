"use server";

import { redirect } from "next/navigation";
import { api } from "../lib/api";

function value(form: FormData, key: string): string { return String(form.get(key) ?? "").trim(); }
function id(form: FormData): number {
  const number = Number(value(form, "id"));
  if (!Number.isSafeInteger(number) || number < 1) throw new Error("Invalid incident identifier");
  return number;
}
function positiveId(form: FormData, key: string): number {
  const number = Number(value(form, key));
  if (!Number.isSafeInteger(number) || number < 1) throw new Error(`Invalid ${key.replace("_", " ")}`);
  return number;
}
function failure(error: unknown): never {
  const message = error instanceof Error ? error.message : "Action failed";
  redirect(`/?error=${encodeURIComponent(message.slice(0, 200))}`);
}
function rssFailure(error: unknown): never {
  const message = error instanceof Error ? error.message : "Action failed";
  redirect(`/rss?error=${encodeURIComponent(message.slice(0, 200))}`);
}

export async function addSource(form: FormData) {
  try { await api("/sources", "POST", { name: value(form, "name"), url: value(form, "url"), language: value(form, "language") }); }
  catch (error) { failure(error); }
  redirect("/");
}

export async function addIncident(form: FormData) {
  let created: { id: number };
  try { created = await api("/incidents", "POST", { title_en: value(form, "title_en"), title_ar: value(form, "title_ar"), category: value(form, "category") }); }
  catch (error) { failure(error); }
  redirect(`/incident/${created.id}`);
}

export async function addFeed(form: FormData) {
  try {
    await api("/feeds", "POST", {
      name: value(form, "name"),
      url: value(form, "url"),
      feed_url: value(form, "feed_url"),
      language: value(form, "language"),
      enabled: form.get("enabled") === "on",
      poll_interval_minutes: Number(value(form, "poll_interval_minutes")),
    });
  } catch (error) { rssFailure(error); }
  redirect("/rss");
}

export async function collectFeed(form: FormData) {
  try { await api(`/feeds/${positiveId(form, "source_id")}/collect`, "POST"); }
  catch (error) { rssFailure(error); }
  redirect("/rss");
}

export async function promoteFeedItem(form: FormData) {
  try {
    await api(`/feed-items/${positiveId(form, "item_id")}/promote`, "POST", {
      title_en: value(form, "title_en"),
      title_ar: value(form, "title_ar"),
      category: value(form, "category"),
    });
  } catch (error) { rssFailure(error); }
  redirect("/rss");
}

export async function attachFeedItem(form: FormData) {
  try {
    await api(`/feed-items/${positiveId(form, "item_id")}/attach`, "POST", {
      incident_id: positiveId(form, "incident_id"),
    });
  } catch (error) { rssFailure(error); }
  redirect("/rss");
}

export async function addEvidence(form: FormData) {
  let incidentId = 0;
  try {
    incidentId = id(form);
    await api(`/incidents/${incidentId}/evidence`, "POST", { source_id: Number(value(form, "source_id")), url: value(form, "url"), text: value(form, "text"), published_at: value(form, "published_at") });
  } catch (error) { failure(error); }
  redirect(`/incident/${incidentId}`);
}

export async function editIncident(form: FormData) {
  let incidentId = 0;
  try {
    incidentId = id(form);
    const keys = ["title_en", "title_ar", "category", "summary_en", "summary_ar", "uncertainty_en", "uncertainty_ar", "location_en", "location_ar", "precision", "occurred_at", "confidence"];
    const fields = Object.fromEntries(keys.map((key) => [key, value(form, key)]));
    await api(`/incidents/${incidentId}`, "PUT", fields);
  } catch (error) { failure(error); }
  redirect(`/incident/${incidentId}`);
}

export async function transition(form: FormData) {
  let incidentId = 0;
  try {
    incidentId = id(form);
    await api(`/incidents/${incidentId}/transition`, "POST", { state: value(form, "state"), reason: value(form, "reason") });
  } catch (error) { failure(error); }
  redirect(`/incident/${incidentId}`);
}

export async function review(form: FormData) {
  let incidentId = 0;
  try {
    incidentId = id(form);
    const keys = ["independence_checked", "time_checked", "location_checked", "contradictions_checked", "person_safety_checked", "operational_safety_checked", "contradictions_acknowledged", "human_approved", "primary_evidence_checked"];
    const flags = Object.fromEntries(keys.map((key) => [key, form.get(key) === "on"]));
    await api(`/incidents/${incidentId}/review`, "POST", { rationale: value(form, "rationale"), ...flags });
  } catch (error) { failure(error); }
  redirect(`/incident/${incidentId}`);
}

export async function exportIncident(form: FormData) {
  let incidentId = 0;
  try {
    incidentId = id(form);
    await api(`/incidents/${incidentId}/export`, "POST", { acknowledged: form.get("acknowledged") === "on" });
  } catch (error) { failure(error); }
  redirect(`/incident/${incidentId}?exported=1`);
}

function deskFailure(error: unknown, page: "intake" | "telegram"): never {
  const message = error instanceof Error ? error.message : "Action failed";
  redirect(`/${page}?error=${encodeURIComponent(message.slice(0, 200))}`);
}

export async function resolveTelegramChannel(form: FormData) {
  let result: { username: string; channel_id: number; title: string };
  try {
    result = await api("/telegram/channels/resolve", "POST", { username: value(form, "username") });
  } catch (error) { deskFailure(error, "telegram"); }
  const params = new URLSearchParams({ candidate: result.username, channel_id: String(result.channel_id), title: result.title });
  redirect(`/telegram?${params.toString()}`);
}

export async function approveTelegramChannel(form: FormData) {
  try {
    await api("/telegram/channels", "POST", {
      username: value(form, "username"), channel_id: positiveId(form, "channel_id"),
      title: value(form, "title"), language: value(form, "language"),
    });
  } catch (error) { deskFailure(error, "telegram"); }
  redirect("/telegram");
}

export async function syncTelegramChannel(form: FormData) {
  try { await api(`/telegram/channels/${positiveId(form, "source_id")}/sync`, "POST"); }
  catch (error) { deskFailure(error, "telegram"); }
  redirect("/telegram");
}

export async function updateTelegramMediaPolicy(form: FormData) {
  try {
    await api(`/telegram/channels/${positiveId(form, "source_id")}/media-policy`, "PUT", { enabled: value(form, "enabled") === "true" });
  } catch (error) { deskFailure(error, "telegram"); }
  redirect("/telegram");
}

export async function promoteIntakeItem(form: FormData) {
  try {
    await api(`/intake-items/${positiveId(form, "item_id")}/promote`, "POST", {
      title_en: value(form, "title_en"), title_ar: value(form, "title_ar"), category: value(form, "category"),
    });
  } catch (error) { deskFailure(error, "intake"); }
  redirect("/intake");
}

export async function attachIntakeItem(form: FormData) {
  try {
    await api(`/intake-items/${positiveId(form, "item_id")}/attach`, "POST", {
      incident_id: positiveId(form, "incident_id"),
    });
  } catch (error) { deskFailure(error, "intake"); }
  redirect("/intake");
}

function publicationFailure(error: unknown, itemId: number): never {
  const detail = error instanceof Error ? error.message : "";
  const message = detail.includes("source changed") ? "Source changed; review the post and preview again."
    : detail.includes("expired") ? "Preview expired; review the post and preview again."
    : detail.includes("deleted") ? "Source post was deleted; review before publishing."
    : "Publication action failed; check the local service and review again.";
  redirect(`/telegram/publication/${itemId}?error=${encodeURIComponent(message)}`);
}

function publicationPayload(form: FormData) {
  return {
    headline_en: value(form, "headline_en"),
    headline_ar: value(form, "headline_ar"),
    source_identity_checked: form.get("source_identity_checked") === "on",
    person_safety_checked: form.get("person_safety_checked") === "on",
    operational_safety_checked: form.get("operational_safety_checked") === "on",
    human_approved: form.get("human_approved") === "on",
  };
}

export async function previewTelegramPublication(form: FormData) {
  const itemId = positiveId(form, "item_id");
  let preview: { draft_hash: string };
  try {
    preview = await api(`/intake-items/${itemId}/publication-preview`, "POST", publicationPayload(form));
  } catch (error) { publicationFailure(error, itemId); }
  redirect(`/telegram/publication/${itemId}?preview=${encodeURIComponent(preview.draft_hash)}`);
}

export async function approveTelegramPublication(form: FormData) {
  const itemId = positiveId(form, "item_id");
  try {
    await api(`/intake-items/${itemId}/publication-approve`, "POST", {
      ...publicationPayload(form), draft_hash: value(form, "draft_hash"),
    });
  } catch (error) { publicationFailure(error, itemId); }
  redirect(`/telegram/publication/${itemId}?approved=1`);
}

export async function correctTelegramPublication(form: FormData) {
  const itemId = positiveId(form, "item_id");
  try {
    await api(`/telegram-publications/${positiveId(form, "publication_id")}/correct`, "POST", {
      ...publicationPayload(form), reason_en: value(form, "reason_en"), reason_ar: value(form, "reason_ar"),
    });
  } catch (error) { publicationFailure(error, itemId); }
  redirect(`/telegram/publication/${itemId}?corrected=1`);
}

export async function withdrawTelegramPublication(form: FormData) {
  const itemId = positiveId(form, "item_id");
  try {
    await api(`/telegram-publications/${positiveId(form, "publication_id")}/withdraw`, "POST", {
      reason_en: value(form, "reason_en"), reason_ar: value(form, "reason_ar"),
      human_approved: form.get("human_approved") === "on",
    });
  } catch (error) { publicationFailure(error, itemId); }
  redirect(`/telegram/publication/${itemId}?withdrawn=1`);
}

function candidateFailure(error: unknown): never {
  if (error instanceof Error && "conflict" in error && error.conflict && typeof error.conflict === "object") {
    const conflict = error.conflict as { kind?: unknown; id?: unknown };
    if ((conflict.kind === "candidate" || conflict.kind === "source") && typeof conflict.id === "number" && Number.isSafeInteger(conflict.id) && conflict.id > 0) {
      const params = new URLSearchParams({ error: `Already recorded as ${conflict.kind} #${conflict.id}. Review the existing record.` });
      if (conflict.kind === "candidate") params.set("candidate", String(conflict.id));
      redirect(`/candidates?${params.toString()}`);
    }
  }
  redirect(`/candidates?error=${encodeURIComponent("Candidate action failed. Check the fields, all five checks for acceptance, and the local service; the URL may already be recorded.")}`);
}

export async function addCandidate(form: FormData) {
  try {
    await api("/candidates", "POST", {
      platform: value(form, "platform"), url: value(form, "url"), name: value(form, "name"),
      language: value(form, "language"), suggestion_reason: value(form, "suggestion_reason"),
    });
  } catch (error) { candidateFailure(error); }
  redirect("/candidates");
}

export async function reviewCandidate(form: FormData) {
  try {
    const keys = ["accessibility_checked", "relevance_checked", "identity_checked", "provenance_checked", "policy_checked"];
    await api(`/candidates/${positiveId(form, "candidate_id")}/reviews`, "POST", {
      decision: value(form, "decision"), reason: value(form, "reason"),
      checks: Object.fromEntries(keys.map((key) => [key, form.get(key) === "on"])),
    });
  } catch (error) { candidateFailure(error); }
  redirect("/candidates");
}
