import { geoMercator } from "d3-geo";
import type { Feature, FeatureCollection, Geometry } from "geojson";
import { feature as topologyFeature } from "topojson-client";
import type { GeometryCollection, Topology } from "topojson-specification";
import countries from "world-atlas/countries-110m.json";
import type { PublicIncident } from "@syosint/schemas";

const SYRIA_NUMERIC_ID = "760";
const MAP_PADDING = 24;
const SYRIA_BOUNDS = {
  minimumLatitude: 32,
  maximumLatitude: 37.5,
  minimumLongitude: 35,
  maximumLongitude: 42.5,
};

let cachedSyriaFeature: Feature<Geometry> | undefined;

export function getSyriaFeature(): Feature<Geometry> {
  if (cachedSyriaFeature) {
    return cachedSyriaFeature;
  }

  const atlas = countries as unknown as Topology<{
    countries: GeometryCollection;
  }>;
  const collection = topologyFeature(
    atlas,
    atlas.objects.countries,
  ) as unknown as FeatureCollection<Geometry>;
  const syria = collection.features.find(
    (candidate) => String(candidate.id) === SYRIA_NUMERIC_ID,
  );

  if (!syria) {
    throw new Error("Bundled map data does not contain Syria (ISO 760).");
  }

  cachedSyriaFeature = {
    ...syria,
    properties: { ...(syria.properties ?? {}), name: "Syria" },
  };

  return cachedSyriaFeature;
}

export function isMarkerEligible(incident: PublicIncident): boolean {
  const { latitude, longitude, precision } = incident.location;

  return (
    (precision === "governorate" || precision === "district") &&
    latitude !== undefined &&
    longitude !== undefined &&
    latitude >= SYRIA_BOUNDS.minimumLatitude &&
    latitude <= SYRIA_BOUNDS.maximumLatitude &&
    longitude >= SYRIA_BOUNDS.minimumLongitude &&
    longitude <= SYRIA_BOUNDS.maximumLongitude
  );
}

export function createSyriaProjection(width: number, height: number) {
  return geoMercator().fitExtent(
    [
      [MAP_PADDING, MAP_PADDING],
      [width - MAP_PADDING, height - MAP_PADDING],
    ],
    getSyriaFeature(),
  );
}

export function projectIncident(
  incident: PublicIncident,
  width: number,
  height: number,
): [number, number] | null {
  if (!isMarkerEligible(incident)) {
    return null;
  }

  const point = createSyriaProjection(width, height)([
    incident.location.longitude!,
    incident.location.latitude!,
  ]);

  return point ? [point[0], point[1]] : null;
}
