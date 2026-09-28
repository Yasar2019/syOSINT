import { readFile, mkdir, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import Ajv2020 from "ajv/dist/2020.js";
import addFormats from "ajv-formats";

const appRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const repositoryRoot = resolve(appRoot, "../..");
const datasets = [
  ["news-wire.v1.json", "public-news-wire.schema.json", "news"],
  ["telegram-wire.v1.json", "public-telegram-wire.schema.json", "Telegram"],
];

export async function syncPublicData(root = repositoryRoot, destinationRoot = resolve(root, "apps/public-dashboard/public")) {
  const ajv = new Ajv2020({ allErrors: true, strict: true });
  addFormats(ajv);
  const validated = [];
  // Validate both inputs before writing either public output.
  for (const [filename, schemaFilename, label] of datasets) {
    const value = JSON.parse(await readFile(resolve(root, "data/public", filename), "utf8"));
    const schema = JSON.parse(await readFile(resolve(root, "packages/schemas/src", schemaFilename), "utf8"));
    const validate = ajv.compile(schema);
    if (!validate(value)) throw new Error(`Invalid public ${label} wire: ${ajv.errorsText(validate.errors)}`);
    const ids = value.entries.map((entry) => entry.id);
    if (new Set(ids).size !== ids.length) throw new Error(`Invalid public ${label} wire: entry ids must be unique`);
    if (label === "Telegram") {
      for (const entry of value.entries) {
        const [, username, messageId] = new URL(entry.url).pathname.split("/");
        if (username.toLowerCase() !== entry.channel.username.toLowerCase() || messageId !== entry.id.split(":").at(-1))
          throw new Error("Invalid public Telegram wire: link does not match approved channel");
        if (![entry.channel.name, entry.headline.en, entry.headline.ar].every((text) => text.trim()))
          throw new Error("Invalid public Telegram wire: empty public headline");
        if (entry.status === "active" ? entry.revisions.length !== 0 : entry.revisions.at(-1)?.action !== entry.status)
          throw new Error("Invalid public Telegram wire: status and revisions differ");
        let previous = Date.parse(entry.approvedAt);
        for (const revision of entry.revisions) {
          const revised = Date.parse(revision.revisedAt);
          if (revised <= previous || !revision.reason.en.trim() || !revision.reason.ar.trim() ||
            (revision.action === "corrected" && (!revision.previousHeadline?.en.trim() || !revision.previousHeadline?.ar.trim())) ||
            (revision.action === "withdrawn" && revision.previousHeadline !== undefined))
            throw new Error("Invalid public Telegram wire: revision history invalid");
          previous = revised;
        }
      }
    }
    validated.push([filename, value]);
  }
  await mkdir(destinationRoot, { recursive: true });
  for (const [filename, value] of validated) {
    await writeFile(resolve(destinationRoot, filename), `${JSON.stringify(value, null, 2)}\n`, "utf8");
  }
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  await syncPublicData();
}
