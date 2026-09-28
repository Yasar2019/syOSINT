import { validatePublicTelegramWire, type PublicTelegramWire } from "@syosint/schemas";
import publicTelegramWire from "../../../../data/public/telegram-wire.v1.json";

export function loadPublicTelegramWire(value: unknown = publicTelegramWire, now = new Date()): PublicTelegramWire {
  const result = validatePublicTelegramWire(value);
  if (!result.ok) throw new Error(`Invalid public Telegram wire: ${result.errors.join("; ")}`);
  const cutoff = now.getTime() - 7 * 24 * 60 * 60 * 1000;
  return {
    ...result.data,
    entries: result.data.entries
      .filter((entry) => Date.parse(entry.publishedAt) >= cutoff && Date.parse(entry.publishedAt) <= now.getTime())
      .sort((left, right) => Date.parse(right.publishedAt) - Date.parse(left.publishedAt) || right.id.localeCompare(left.id)),
  };
}
