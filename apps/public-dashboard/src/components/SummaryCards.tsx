import type { PublicIncident } from "@syosint/schemas";
import type { Dictionary } from "../i18n/types";

export function SummaryCards({
  incidents,
  dictionary,
}: {
  incidents: PublicIncident[];
  dictionary: Dictionary;
}) {
  const verified = incidents.filter((item) =>
    ["corroborated", "verified"].includes(item.confidence),
  ).length;
  const needsAttention = incidents.filter((item) =>
    ["unverified", "disputed"].includes(item.confidence),
  ).length;

  return (
    <section className="summary-grid" aria-label={dictionary.summary.total}>
      <article>
        <strong>{incidents.length}</strong>
        <span>{dictionary.summary.total}</span>
      </article>
      <article>
        <strong>{verified}</strong>
        <span>{dictionary.summary.verified}</span>
      </article>
      <article>
        <strong>{needsAttention}</strong>
        <span>{dictionary.summary.needsAttention}</span>
      </article>
    </section>
  );
}
