import { describe, expect, it } from "vitest";
import { getSyriaFeature, isMarkerEligible, projectIncident } from "./map";
import { loadPublicDataset } from "./load-public-dataset";

describe("map safety", () => {
  it("extracts Syria from the bundled Natural Earth-derived atlas", () => {
    const feature = getSyriaFeature();

    expect(feature.type).toBe("Feature");
    expect(feature.properties).toMatchObject({ name: "Syria" });
  });

  it("suppresses withheld and outside-bounds coordinates", () => {
    const incident = structuredClone(loadPublicDataset().incidents[0]);
    incident.location.precision = "withheld";
    expect(isMarkerEligible(incident)).toBe(false);

    incident.location.precision = "governorate";
    incident.location.latitude = 0;
    incident.location.longitude = 0;
    expect(isMarkerEligible(incident)).toBe(false);
    expect(projectIncident(incident, 640, 480)).toBeNull();
  });

  it("projects safe synthetic Syria coordinates inside the viewport", () => {
    const incident = loadPublicDataset().incidents.find(
      (item) => item.location.latitude !== undefined,
    )!;

    const point = projectIncident(incident, 640, 480);

    expect(point).not.toBeNull();
    expect(point![0]).toBeGreaterThanOrEqual(0);
    expect(point![0]).toBeLessThanOrEqual(640);
    expect(point![1]).toBeGreaterThanOrEqual(0);
    expect(point![1]).toBeLessThanOrEqual(480);
  });
});
