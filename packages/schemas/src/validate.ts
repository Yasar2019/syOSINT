import Ajv2020 from "ajv/dist/2020";
import addFormats from "ajv-formats";
import incidentSchema from "./public-incident.schema.json";
import newsWireSchema from "./public-news-wire.schema.json";
import telegramWireSchema from "./public-telegram-wire.schema.json";
import type { PublicDataset, PublicNewsWire, PublicTelegramWire } from "./types";

export type ValidationResult =
  | { ok: true; data: PublicDataset }
  | { ok: false; errors: string[] };

export type NewsWireValidationResult =
  | { ok: true; data: PublicNewsWire }
  | { ok: false; errors: string[] };

const ajv = new Ajv2020({ allErrors: true, strict: true });
addFormats(ajv);
const validate = ajv.compile<PublicDataset>(incidentSchema);
const validateNewsWire = ajv.compile<PublicNewsWire>(newsWireSchema);
const validateTelegramWire = ajv.compile<PublicTelegramWire>(telegramWireSchema);

export function validatePublicDataset(value: unknown): ValidationResult {
  if (!validate(value)) {
    return {
      ok: false,
      errors: (validate.errors ?? []).map(
        (error) => `${error.instancePath || "/"} ${error.message}`,
      ),
    };
  }

  const ids = value.incidents.map((incident) => incident.id);
  if (new Set(ids).size !== ids.length) {
    return { ok: false, errors: ["incident ids must be unique"] };
  }

  const inconsistentSources = value.incidents.find(
    (incident) => incident.sourceCount < incident.sources.length,
  );
  if (inconsistentSources) {
    return {
      ok: false,
      errors: [
        `incident ${inconsistentSources.id} sourceCount cannot be smaller than sources.length`,
      ],
    };
  }

  return { ok: true, data: value };
}

export function validatePublicNewsWire(
  value: unknown,
): NewsWireValidationResult {
  if (!validateNewsWire(value)) {
    return {
      ok: false,
      errors: (validateNewsWire.errors ?? []).map(
        (error) => `${error.instancePath || "/"} ${error.message}`,
      ),
    };
  }

  const ids = value.entries.map((entry) => entry.id);
  if (new Set(ids).size !== ids.length) {
    return { ok: false, errors: ["news-wire entry ids must be unique"] };
  }

  const sourceStateIds = value.sourceStates.map((state) => state.id);
  if (new Set(sourceStateIds).size !== sourceStateIds.length) {
    return { ok: false, errors: ["news-wire source-state ids must be unique"] };
  }

  const attributedSourceIds = new Set(sourceStateIds);
  if (value.entries.some((entry) => !attributedSourceIds.has(entry.sourceId))) {
    return {
      ok: false,
      errors: ["news-wire entries must reference an attributed source state"],
    };
  }

  return { ok: true, data: value };
}

export type TelegramWireValidationResult =
  | { ok: true; data: PublicTelegramWire }
  | { ok: false; errors: string[] };

export function validatePublicTelegramWire(value: unknown): TelegramWireValidationResult {
  if (!validateTelegramWire(value)) {
    return { ok: false, errors: (validateTelegramWire.errors ?? []).map(
      (error) => `${error.instancePath || "/"} ${error.message}`,
    ) };
  }
  const ids = new Set<string>();
  for (const entry of value.entries) {
    if (ids.has(entry.id)) return { ok: false, errors: ["telegram entry ids must be unique"] };
    ids.add(entry.id);
    const url = new URL(entry.url);
    const username = url.pathname.split("/")[1];
    if (username.toLowerCase() !== entry.channel.username.toLowerCase() ||
        entry.id.split(":").at(-1) !== url.pathname.split("/")[2]) {
      return { ok: false, errors: ["telegram link must match approved channel username"] };
    }
    if (![entry.channel.name, entry.headline.en, entry.headline.ar].every((field) => field.trim())) {
      return { ok: false, errors: ["public names and headlines cannot be blank"] };
    }
    if (entry.status === "active" && entry.revisions.length > 0 ||
        entry.status !== "active" && entry.revisions.at(-1)?.action !== entry.status) {
      return { ok: false, errors: ["telegram status must match latest revision"] };
    }
    let previous = Date.parse(entry.approvedAt);
    for (const revision of entry.revisions) {
      const at = Date.parse(revision.revisedAt);
      if (at <= previous || !revision.reason.en.trim() || !revision.reason.ar.trim()) {
        return { ok: false, errors: ["telegram revisions must be ordered and have bilingual reasons"] };
      }
      previous = at;
    }
  }
  return { ok: true, data: value };
}
