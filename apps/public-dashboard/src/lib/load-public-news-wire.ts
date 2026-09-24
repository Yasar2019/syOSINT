import {
  validatePublicNewsWire,
  type PublicNewsWire,
} from "@syosint/schemas";
import publicNewsWire from "../../../../data/public/news-wire.v1.json";

export function loadPublicNewsWire(
  value: unknown = publicNewsWire,
): PublicNewsWire {
  const result = validatePublicNewsWire(value);
  if (!result.ok) {
    throw new Error(`Invalid public news wire: ${result.errors.join("; ")}`);
  }

  return {
    ...result.data,
    sources: { ...result.data.sources },
    entries: [...result.data.entries].sort(
      (left, right) =>
        Date.parse(right.publishedAt) - Date.parse(left.publishedAt) ||
        right.id.localeCompare(left.id),
    ),
  };
}
