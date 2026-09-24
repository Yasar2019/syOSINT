import { readFile, mkdir, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import Ajv2020 from "ajv/dist/2020.js";
import addFormats from "ajv-formats";

const appRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const repositoryRoot = resolve(appRoot, "../..");
const source = resolve(repositoryRoot, "data/public/news-wire.v1.json");
const schemaPath = resolve(repositoryRoot, "packages/schemas/src/public-news-wire.schema.json");
const destination = resolve(appRoot, "public/news-wire.v1.json");
const value = JSON.parse(await readFile(source, "utf8"));
const schema = JSON.parse(await readFile(schemaPath, "utf8"));
const ajv = new Ajv2020({ allErrors: true, strict: true });
addFormats(ajv);
const validate = ajv.compile(schema);

if (!validate(value)) {
  throw new Error(`Invalid public news wire: ${ajv.errorsText(validate.errors)}`);
}
const ids = value.entries.map((entry) => entry.id);
if (new Set(ids).size !== ids.length) {
  throw new Error("Invalid public news wire: entry ids must be unique");
}

await mkdir(dirname(destination), { recursive: true });
await writeFile(destination, `${JSON.stringify(value, null, 2)}\n`, "utf8");
