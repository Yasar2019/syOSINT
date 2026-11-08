# Detailed Map Implementation Plan

> Use native execution with a fresh whole-branch review.

**Goal:** Detailed free map on existing static dashboard.
**Architecture:** MapLibre client map using OpenFreeMap with existing SVG fallback; no backend changes.
**Spec:** docs/superpowers/specs/2026-11-07-detailed-map-design.md

## Global constraints
Public generalized coordinates only; no withdrawn/withheld/private locations; no keys/payments; preserve attribution, keyboard list, Arabic controls and static export.

## Review focus
Unmount during lazy import, tile failure/WebGL absence, filter updates, callbacks capturing stale locale, mobile scroll/resize, SSR.

### Task 1: Marker and fallback tests
- [ ] Test withdrawn/nonfinite suppression and existing safe marker list before implementation; observe red.
- [ ] Implement shared eligibility guard and fallback map.
### Task 2: Detailed renderer and controls
- [ ] Test client lifecycle/marker changes/failure and localized controls with mocked rendering boundary; observe red.
- [ ] Add MapLibre, free basemap styles, lazy lifecycle cleanup, toolbar and responsive CSS.
### Task 3: Release
- [ ] Full JS/lint/types/build/audit/policy; deterministic browser fallback/control checks in CI; independent review.
- [ ] Document provider/attribution/fallback and release with green CI.
