# Methodology

syOSINT separates fast external reporting from reviewed incident intelligence. That distinction is structural, not merely visual.

## Live News Wire

The Live News Wire is an automatic index of original headlines from the repository's reviewed RSS/Atom allowlist. A scheduled job runs every 30 minutes. For broad feeds, a headline is included only when Unicode-normalized, case-insensitive text contains one of the source's committed Syria-topic terms.

The wire performs no translation, summarization, event extraction, credibility scoring, or incident matching. Entries are deduplicated through deterministic source-native IDs, canonical HTTPS URLs, and normalized headline/time fingerprints. Tracking parameters are removed conservatively; similarity alone never merges records.

The public projection includes only attribution and navigation metadata: publisher, original-language headline, language, publication/collection time, stable identifier, and canonical publisher link. It excludes descriptions, article bodies, images, locations, private notes, evidence, response headers, and quarantine data. Entries expire after seven days and the wire is capped at 500 records.

Every wire item is labeled **Unverified external reporting**. Inclusion means only that an allowlisted publisher placed a matching headline in its feed. It does not mean syOSINT has verified the underlying claim, endorses the publisher, or determined that separate headlines describe the same event. Headline-only filtering can miss indirectly worded reports and can produce ambiguous matches.

The displayed refresh time and aggregate source state help readers distinguish a current wire from a delayed one. A delayed feed does not imply that no news exists. The last valid deployment remains online when collection, validation, or building fails.

## Reviewed incidents

Reviewed incidents are created and published through the private analyst workflow. Analysts inspect public source material, preserve provenance, attach evidence, write bilingual public summaries, select category and safe geographic precision, record uncertainty and confidence rationale, and complete verification and safety checks. Publication is explicit and fails closed.

Promoting a wire item merely creates a traceable triage starting point. It never copies a publisher headline into an approved incident automatically and never invents a summary, category, location, confidence label, or verification state. Additional reports may be attached only through the private workflow.

Consequently, the wire's speed and the incident section's evidentiary judgment answer different questions:

- the wire says, “an approved external source is currently reporting this headline”; and
- an incident says, “syOSINT analysts reviewed evidence and are publishing this bounded claim with stated uncertainty.”

## Safety and corrections

Neither path authorizes private-source access, person tracking, facial recognition, doxxing, or precise live tactical publication. Automatic RSS projection cannot contain sensitive locations or ordinary-person identities beyond text already present in a publisher's headline. Analysts must still generalize, delay, or withhold sensitive incident details.

Publisher corrections flow into later feed entries but do not silently rewrite reviewed incidents. Formal incident correction and withdrawal tooling is planned for Milestone 5; until it exists, the prototype must not be used to publish cases that require that lifecycle.

Source governance, operational health, quarantine, and stale recovery are documented in [RSS/Atom Source and Operations Policy](../source-policy/RSS.md).
