import type { PublicIncident } from "@syosint/schemas";
import type { Dictionary, Locale } from "../i18n/types";
import { ConfidenceBadge } from "./ConfidenceBadge";

export function IncidentDetail({
  incident,
  locale,
  dictionary,
  onClose,
}: {
  incident: PublicIncident;
  locale: Locale;
  dictionary: Dictionary;
  onClose: () => void;
}) {
  return (
    <aside className="incident-detail" aria-labelledby="incident-detail-title">
      <div className="detail-heading">
        <div>
          <p className="eyebrow">{dictionary.detail.title}</p>
          <h2 id="incident-detail-title">{incident.title[locale]}</h2>
        </div>
        <button type="button" onClick={onClose}>
          {dictionary.detail.close}
        </button>
      </div>
      <ConfidenceBadge confidence={incident.confidence} dictionary={dictionary} />
      <p>{incident.summary[locale]}</p>
      <section>
        <h3>{dictionary.detail.uncertainty}</h3>
        <p>{incident.uncertainty[locale]}</p>
      </section>
      <section>
        <h3>{dictionary.detail.sources}</h3>
        <ul>
          {incident.sources.map((source) => (
            <li key={source.id}>
              <a href={source.url} target="_blank" rel="noopener noreferrer">
                {source.label[locale]}
                <span className="visually-hidden">
                  {` (${dictionary.accessibility.externalLink})`}
                </span>
              </a>
            </li>
          ))}
        </ul>
      </section>
      <section>
        <h3>{dictionary.detail.corrections}</h3>
        {incident.corrections.length === 0 ? (
          <p>{dictionary.detail.noCorrections}</p>
        ) : (
          <ol>
            {incident.corrections.map((correction) => (
              <li key={`${correction.correctedAt}-${correction.changedFields.join("-")}`}>
                <time dateTime={correction.correctedAt}>{correction.correctedAt}</time>
                <p>{correction.reason[locale]}</p>
              </li>
            ))}
          </ol>
        )}
      </section>
    </aside>
  );
}
