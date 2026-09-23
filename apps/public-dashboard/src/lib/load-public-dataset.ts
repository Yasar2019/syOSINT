import { validatePublicDataset, type PublicDataset } from "@syosint/schemas";
import publicDataset from "../../../../data/public/incidents.v1.json";

export function loadPublicDataset(): PublicDataset {
  const result = validatePublicDataset(publicDataset);

  if (!result.ok) {
    throw new Error(`Invalid public dataset: ${result.errors.join("; ")}`);
  }

  return result.data;
}
