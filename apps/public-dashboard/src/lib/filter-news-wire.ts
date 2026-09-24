import type { PublicNewsWireEntry } from "@syosint/schemas";

export interface NewsWireFilters {
  sourceIds: string[];
  languages: Array<"en" | "ar">;
}

export function filterNewsWire(
  entries: readonly PublicNewsWireEntry[],
  filters: NewsWireFilters,
): PublicNewsWireEntry[] {
  return entries.filter(
    (entry) =>
      (filters.sourceIds.length === 0 ||
        filters.sourceIds.includes(entry.sourceId)) &&
      (filters.languages.length === 0 ||
        filters.languages.includes(entry.language)),
  );
}
