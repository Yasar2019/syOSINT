import Ajv2020 from "ajv/dist/2020";
import addFormats from "ajv-formats";
import schema from "./public-incident.schema.json";
import type { PublicDataset } from "./types";

export type ValidationResult =
  | { ok: true; data: PublicDataset }
  | { ok: false; errors: string[] };

const ajv = new Ajv2020({ allErrors: true, strict: true });
addFormats(ajv);
const validate = ajv.compile<PublicDataset>(schema);

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
