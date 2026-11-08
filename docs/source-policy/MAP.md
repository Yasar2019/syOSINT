# Public basemap

The detailed map uses MapLibre GL JS 6.17.0 (BSD-3-Clause) and OpenFreeMap vector basemaps, derived from OpenStreetMap/OpenMapTiles. The provider currently permits free public and commercial use without an account, key or map-view quota. No billing integration is present. The donation-funded public service has no SLA; this is a dependency on third-party availability, not a promise of permanent free hosting.

- Library/license: https://github.com/maplibre/maplibre-gl-js
- Provider/terms and attribution: https://openfreemap.org/
- Styles/integration: https://openfreemap.org/quick_start/
- Reference architecture researched: https://github.com/koala73/worldmonitor/blob/main/docs/getting-started.mdx

WorldMonitor uses MapLibre plus deck.gl for desktop overlays. syOSINT uses MapLibre alone because its current incident volume does not require another visualization engine. No WorldMonitor application code is copied.

The default dark style and alternate street style show geographic features such as roads, settlements and borders. Attribution remains visible. Map tiles/fonts/styles load directly in the viewer's browser from the provider, which can see ordinary request metadata and the viewport being viewed. Report text, private analyst data and evidence are never submitted to the map provider. No geocoding service is used.

Only existing public coordinates with governorate/district precision inside the Syria bounds are eligible for incident markers. Withdrawn, withheld, country-only, nonfinite and outside-bounds locations are excluded. Zooming into the basemap does not add accuracy to a generalized incident location. Source reports and raw Telegram material are not automatically placed on the map.

The client lazily imports the renderer; it does not continuously animate. Native cooperative gestures preserve ordinary page scrolling, and localized toolbar buttons provide zoom and Syria reset. The accessible location list remains available. Without WebGL2, after an initialization/service error, or after a 15-second load timeout, the bundled SVG overview remains visible and a retry action is available. Style changes/unmounts clean up the prior map and markers. A regional internet outage does not prevent using the overview/list.

Acceptance combines mocked rendering-boundary unit tests with real MapLibre browser rendering against a deterministic style. The latter verifies the engine, canvas, marker clicks and style changes without requiring a public tile service during CI. Provider style availability is checked separately; real-network cartographic coverage remains provider-owned.
