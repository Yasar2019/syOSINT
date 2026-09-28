import { copyFile, mkdir, mkdtemp, readFile, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { syncPublicData } from "./sync-public-data.mjs";

const root = resolve(import.meta.dirname, "../../..");

async function fixture() {
  const temporary = await mkdtemp(resolve(tmpdir(), "syosint-sync-"));
  for (const path of [
    "data/public/news-wire.v1.json", "data/public/telegram-wire.v1.json",
    "packages/schemas/src/public-news-wire.schema.json", "packages/schemas/src/public-telegram-wire.schema.json",
  ]) {
    await mkdir(dirname(resolve(temporary, path)), { recursive: true });
    await copyFile(resolve(root, path), resolve(temporary, path));
  }
  return temporary;
}

describe("static public data sync", () => {
  it("copies both validated public contracts", async () => {
    const folder = await fixture();
    await syncPublicData(folder);
    expect(JSON.parse(await readFile(resolve(folder, "apps/public-dashboard/public/telegram-wire.v1.json"), "utf8"))).toHaveProperty("entries");
  });
  it("rejects private Telegram fields before copying either dataset", async () => {
    const folder = await fixture();
    const path = resolve(folder, "data/public/telegram-wire.v1.json");
    const value = JSON.parse(await readFile(path, "utf8"));
    value.entries = [{ rawText: "private" }];
    await writeFile(path, JSON.stringify(value));
    await expect(syncPublicData(folder)).rejects.toThrow("Invalid public Telegram wire");
    await expect(readFile(resolve(folder, "apps/public-dashboard/public/news-wire.v1.json"))).rejects.toThrow();
  });
});
