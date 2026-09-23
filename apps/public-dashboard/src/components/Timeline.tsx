import type { PublicIncident } from "@syosint/schemas";
import type { Dictionary, Locale } from "../i18n/types";

interface TimelineGroup {
  date: string;
  incidents: PublicIncident[];
}

function groupByUtcDate(incidents: PublicIncident[]): TimelineGroup[] {
  const groups = new Map<string, PublicIncident[]>();

  for (const incident of [...incidents].sort((a, b) => b.occurredAt.localeCompare(a.occurredAt))) {
    const date = incident.occurredAt.slice(0, 10);
    groups.set(date, [...(groups.get(date) ?? []), incident]);
  }

  return [...groups].map(([date, groupedIncidents]) => ({
    date,
    incidents: groupedIncidents,
  }));
}

export function Timeline({
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
  const groups = groupByUtcDate(incidents);

  return (
    <section className="timeline" aria-labelledby="timeline-title">
      <h2 id="timeline-title">{dictionary.timeline.title}</h2>
      <ol className="timeline-days">
        {groups.map((group) => (
          <li key={group.date}>
            <time dateTime={group.date}>
              {new Intl.DateTimeFormat(locale === "ar" ? "ar" : "en", {
                dateStyle: "medium",
                timeZone: "UTC",
              }).format(new Date(`${group.date}T00:00:00Z`))}
            </time>
            <ol>
              {group.incidents.map((incident) => (
                <li key={incident.id}>
                  <button type="button" onClick={() => onSelect(incident.id)}>
                    <time dateTime={incident.occurredAt}>
                      {new Intl.DateTimeFormat(locale === "ar" ? "ar" : "en", {
                        hour: "2-digit",
                        minute: "2-digit",
                        hour12: false,
                        timeZone: "UTC",
                      }).format(new Date(incident.occurredAt))}
                    </time>
                    <span>{incident.title[locale]}</span>
                  </button>
                </li>
              ))}
            </ol>
          </li>
        ))}
      </ol>
    </section>
  );
}
