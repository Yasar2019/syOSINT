import { geoPath } from "d3-geo";
import type { PublicIncident } from "@syosint/schemas";
import type { Dictionary, Locale } from "../i18n/types";
import {
  createSyriaProjection,
  getSyriaFeature,
  projectIncident,
} from "../lib/map";

const WIDTH = 640;
const HEIGHT = 480;

export function SyriaMap({
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
  const projection = createSyriaProjection(WIDTH, HEIGHT);
  const countryPath = geoPath(projection)(getSyriaFeature()) ?? "";
  const markers = incidents.flatMap((incident) => {
    const point = projectIncident(incident, WIDTH, HEIGHT);
    return point ? [{ incident, point }] : [];
  });

  function handleMarkerKeyDown(event: React.KeyboardEvent<SVGGElement>, id: string) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onSelect(id);
    }
  }

  return (
    <section className="situation-map" aria-labelledby="syria-map-title">
      <div className="section-heading">
        <h2 id="syria-map-title">{dictionary.map.title}</h2>
        <p id="syria-map-description">{dictionary.map.description}</p>
      </div>
      <svg
        className="map-canvas"
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        role="img"
        aria-labelledby="syria-map-svg-title"
        aria-describedby="syria-map-svg-description"
      >
        <title id="syria-map-svg-title">{dictionary.map.title}</title>
        <desc id="syria-map-svg-description">{dictionary.map.description}</desc>
        <path className="country-shape" d={countryPath} />
        {markers.map(({ incident, point }) => (
          <g
            key={incident.id}
            className="map-marker"
            role="button"
            tabIndex={0}
            aria-label={`${dictionary.accessibility.openIncident}: ${incident.title[locale]}; ${dictionary.status[incident.status]}; ${dictionary.confidence[incident.confidence]}`}
            transform={`translate(${point[0]} ${point[1]})`}
            onClick={() => onSelect(incident.id)}
            onKeyDown={(event) => handleMarkerKeyDown(event, incident.id)}
          >
            <circle r="11" className="marker-halo" />
            <circle r="5" className={`marker-dot confidence-${incident.confidence}`} />
          </g>
        ))}
      </svg>
      <ol className="map-location-list" aria-label={dictionary.map.title}>
        {markers.map(({ incident }) => (
          <li key={incident.id}>
            <button type="button" onClick={() => onSelect(incident.id)}>
              <span>{incident.location[locale]}</span>
              <small>{incident.title[locale]}</small>
            </button>
          </li>
        ))}
      </ol>
    </section>
  );
}
