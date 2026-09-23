"use server";

import { redirect } from "next/navigation";
import { api } from "../lib/api";

function value(form: FormData, key: string): string { return String(form.get(key) ?? "").trim(); }
function id(form: FormData): number {
  const number = Number(value(form, "id"));
  if (!Number.isSafeInteger(number) || number < 1) throw new Error("Invalid incident identifier");
  return number;
}
function failure(error: unknown): never {
  const message = error instanceof Error ? error.message : "Action failed";
  redirect(`/?error=${encodeURIComponent(message.slice(0, 200))}`);
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
    const keys = ["independence_checked", "time_checked", "location_checked", "contradictions_checked", "person_safety_checked", "operational_safety_checked", "contradictions_acknowledged", "human_approved"];
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
