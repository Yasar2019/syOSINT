# Dependency audit review — 2026-10-12

PR #21 refreshes Next.js/eslint-config-next to 16.4.0, Vitest to 4.1.11, and secretlint/preset to 13.0.7. It pins patched transitive source-map-js 1.2.2 and sharp 0.35.5. The existing high/critical audit threshold remains active.

## Proposed scoped exception requiring owner review before merge

`CVE-2026-93687` / [GHSA-vfj7-8cjw-p6xm](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm) affects braces <=3.0.3. The official advisory lists no patched version; npm's current release is 3.0.3. The remaining dependency path is eslint-config-next → @next/eslint-plugin-next → fast-glob → micromatch → braces. secretlint's updated walker no longer contributes this dependency.

The reported issue is stack exhaustion from attacker-controlled deeply nested glob patterns. This dependency is used by the development lint tool with repository-controlled patterns and configuration; collected RSS/Telegram content and public dashboard requests never supply glob patterns. A malicious contributor who can edit the executable lint configuration already has the ability to execute code in that build environment. This review does not claim braces is patched or generally safe.

The current branch does not suppress this advisory. If the owner accepts the proposed exception, package.json would list only this CVE. All other advisories remain subject to the audit threshold; no registry error, vulnerability class, production dependency, or unfixable-advisory category is ignored. PR #21 must remain unmerged until the owner accepts this specific build-tool exposure decision. Remove the exception when an upstream patch or a maintained replacement eliminates the affected dependency. Reassess it before adding any feature that accepts external glob patterns.

The JavaScript audit runs in an independent CI job so test evidence can be collected while it fails. Overall CI remains failed and the Pages workflow still requires overall CI success.

Verification: before merge, audit must report no unexcepted high/critical issues, policy scanning must still pass, and all tests/builds/browser workflows must pass with the updated lockfile.
