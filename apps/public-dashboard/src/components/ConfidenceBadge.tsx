import type { ConfidenceLabel } from "@syosint/schemas";
import type { Dictionary } from "../i18n/types";

const icons: Record<ConfidenceLabel, string> = {
  unverified: "?",
  developing: "◔",
  corroborated: "✓",
  verified: "✓✓",
  disputed: "!",
  false: "×",
};

export function ConfidenceBadge({
  confidence,
  dictionary,
}: {
  confidence: ConfidenceLabel;
  dictionary: Dictionary;
}) {
  return (
    <span className={`confidence-badge confidence-${confidence}`}>
      <span aria-hidden="true">{icons[confidence]}</span>
      <span>{dictionary.confidence[confidence]}</span>
    </span>
  );
}
