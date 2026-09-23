import type { PublicIncident } from "@syosint/schemas";
import type { Dictionary, Locale } from "../i18n/types";
import { IncidentCard } from "./IncidentCard";

export function IncidentFeed({
  incidents,
  locale,
  dictionary,
  onSelect,
}: {
  incidents: PublicIncident[];
  locale: Locale;
  dictionary: Dictionary;
  onSelect: (id: string) => void;
}) {
  return (
    <section className="incident-feed" aria-labelledby="incident-feed-title">
      <h2 id="incident-feed-title">{dictionary.feed.title}</h2>
      {incidents.length === 0 ? (
        <p className="empty-state">{dictionary.feed.empty}</p>
      ) : (
        <div className="incident-list">
          {incidents.map((incident) => (
            <IncidentCard
              key={incident.id}
              incident={incident}
              locale={locale}
              dictionary={dictionary}
              onSelect={onSelect}
            />
          ))}
        </div>
      )}
    </section>
  );
}
