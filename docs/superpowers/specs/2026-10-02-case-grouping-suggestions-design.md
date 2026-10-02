# Milestone 5: private case grouping suggestions

**Scope:** next independent Milestone 5 slice, after candidate-source review  
**Intent:** help one analyst notice that separately created cases may describe the same event, without making a credibility judgment or merging records automatically.

## Outcome

When an analyst edits a case with a category, a UTC event time, and a private governorate, its private case page shows a short list of other cases with the same category and governorate whose event times are within six hours. Each suggestion links to the other case and shows the time difference and state. The analyst can compare their evidence and choose an existing manual action. A suggestion is a navigation aid, not an assertion that reports corroborate one another.

The feature does not change collection, candidate-source review, incident status, evidence, publication eligibility, or the public dashboard. It never calls an AI service or processes raw Telegram post text to infer an event or a location.

## Matching inputs and rule

- Add an optional, controlled `private_governorate` value to the existing incident edit request and private case form. The options are Syria's 14 governorates plus an unset choice. The selection is analyst supplied and is not copied into the public export. Existing cases without a selection remain valid.
- Use the existing human-entered `occurred_at` and `category` fields. Only timezone-aware timestamps are eligible; compare instants in UTC. An incomplete case yields no suggestions.
- Compare other non-withdrawn cases with the same category and private governorate. Ignore the current case, records without a valid timezone-aware event time, and records more than six hours apart. Return at most ten, ordered by absolute time difference and then case ID. Exact equality is allowed; the boundary is inclusive.
- The API returns only case ID, state, English and Arabic analyst titles, UTC event time, governorate, and the time difference. It never returns evidence text, Telegram posts, coordinates, notes, or a score. The endpoint is private and read only.
- Do not infer that two source reports are independent, that the cases are duplicates, or that either is accurate. A matching category, time, and governorate is deliberately weak evidence and the UI says so.

## Components

1. Add a strict governorate enum to `IncidentEdit`; preserve it in the incident's existing JSON fields, with no schema migration. The edit form sends either one allowed value or no selection. Existing public export explicitly selects its own fields and never serializes this private facet.
2. A small pure matcher accepts an incident and candidate incidents and applies the deterministic rule. `GET /incidents/{id}/related` loads same-category/governorate candidates from the local database, then calls the matcher; unknown IDs return 404. No record is created or mutated by the endpoint.
3. The private incident detail page shows the related-case links after its editorial form. An empty or incomplete case explains that the suggestions need event time and governorate. The page never supplies a one-click merge or changes the existing attach/promote actions.

## Safety and limits

The feature runs only against the local analyst database. It reads analyst-authored fields, not intake text. No matching result is exported publicly, logged with raw content, or sent to AI/ML. A withdrawn case is excluded. The endpoint bounds output to ten and filters candidates in the database by category and governorate before parsing times; it does not scan source content. Inputs remain strict and invalid governorate values return 422.

## Verification

API tests cover missing metadata, exact boundary, different category/governorate, timezone offsets, malformed and naive historical times, withdrawn/self exclusion, deterministic order and limit, invalid value rejection, and no mutation or public-export field leakage. Desk tests cover the selector, links and no automatic-merge wording, empty state, and API failure handling. CI runs the existing Python, TypeScript, build, and browser gates with synthetic records only.

## Deferred

Cross-language text matching, geocoding, raw RSS/Telegram content analysis, suggested source independence, persisted dismissals, and automatic incident merging are outside this slice. The analyst continues to attach evidence manually after comparing cases.
