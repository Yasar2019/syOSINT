import type { PublicIncident } from "@syosint/schemas";
import type { Dictionary, Locale } from "../i18n/types";
import { ConfidenceBadge } from "./ConfidenceBadge";

export function IncidentCard({
  incident,
  locale,
  dictionary,
  onSelect,
}: {
  incident: PublicIncident;
  locale: Locale;
  dictionary: Dictionary;
  onSelect: (id: string) => void;
}) {
  const timestamp = new Intl.DateTimeFormat(locale === "ar" ? "ar" : "en", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  }).format(new Date(incident.occurredAt));

  if (incident.status === "withdrawn") {
    const notice = incident.corrections.at(-1);
    return <article className="incident-card" data-testid="incident-card">
      <strong>{dictionary.status.withdrawn}</strong><h2>{dictionary.detail.withdrawnTitle}</h2>
      <p>{notice?.reason[locale] ?? dictionary.detail.withdrawnTitle}</p>
      <time dateTime={incident.updatedAt}>{incident.updatedAt}</time>
      <button type="button" onClick={() => onSelect(incident.id)}>{dictionary.feed.viewDetails}</button>
    </article>;
  }
  return (
    <article className="incident-card" data-testid="incident-card">
      <div className="incident-card-heading">
        <ConfidenceBadge confidence={incident.confidence} dictionary={dictionary} />
        <span className={`incident-status status-${incident.status}`}>
          {dictionary.status[incident.status]}
        </span>
      </div>
      <p className="incident-categories">
        {incident.categories.map((category) => dictionary.categories[category]).join(" · ")}
      </p>
      <h3>{incident.title[locale]}</h3>
      <p>{incident.summary[locale]}</p>
      {incident.status === "corrected" && incident.corrections.slice(-1).map((correction) => <section key={correction.correctedAt}><time dateTime={correction.correctedAt}>{correction.correctedAt}</time><p>{correction.reason[locale]}</p><p>{dictionary.detail.changedFields}: {correction.changedFields.map((field) => dictionary.changedFields[field] ?? dictionary.detail.otherField).join(", ")}</p></section>)}
      <dl className="incident-meta">
        <div>
          <dt>{dictionary.detail.occurred}</dt>
          <dd>{timestamp} UTC</dd>
        </div>
        <div>
          <dt>{dictionary.map.title}</dt>
          <dd>{incident.location[locale]}</dd>
        </div>
        <div>
          <dt>{dictionary.detail.sources}</dt>
          <dd>{incident.sourceCount}</dd>
        </div>
      </dl>
      <button type="button" onClick={() => onSelect(incident.id)}>
        {dictionary.feed.viewDetails}
      </button>
    </article>
  );
}
