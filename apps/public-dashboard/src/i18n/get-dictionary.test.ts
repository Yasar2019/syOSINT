import { describe, expect, it } from "vitest";
import { getDictionary, getDirection } from "./get-dictionary";

function objectPaths(value: object, prefix = ""): string[] {
  return Object.entries(value).flatMap(([key, child]) => {
    const path = prefix ? `${prefix}.${key}` : key;
    return typeof child === "object" && child !== null
      ? objectPaths(child as object, path)
      : [path];
  });
}

describe("locale dictionaries", () => {
  it("uses right-to-left direction only for Arabic", () => {
    expect(getDirection("ar")).toBe("rtl");
    expect(getDirection("en")).toBe("ltr");
  });

  it("keeps English and Arabic dictionary structures identical", () => {
    expect(objectPaths(getDictionary("ar")).sort()).toEqual(
      objectPaths(getDictionary("en")).sort(),
    );
  });
});
