# Connection verification, 2026-11-04

The live service and separately built Microsoft fork were exercised in the Codex in-app browser on Windows. All records used synthetic data.

- Final integration base: `cb19a58801adf61332c9bcd4b4a418e50c61d595`; adapter code: `b37f4e6bc22a3074bd974a5c661f547bb9fde5a0`.
- Microsoft code: `0f0894b3937116f42aef6db568e3b33a955addb3`. Full opt-in build, TypeScript and lint passed; independent focused review passed 15 tests.
- Full extension suite after the YAML review fix: **138 passed, 1 skipped** in 96.06 seconds. The skipped Windows symbolic-link fixture could not be created. Hard-link and actual loopback HTTP cases passed with fixture permissions.
- Independent backend review passed all 52 connection/HTTP tests; no actionable findings. Its reviewed source was unchanged by the rebase.
- Flow-style YAML initially failed a regression test. JSON syntax errors now fall back to the same safe YAML parser; duplicate keys, non-finite values, aliases and explicit tags remain rejected. An independent follow-up passed 18 parser/source tests; the author passed all 59 connection/HTTP tests.
- NVIDIA's pinned `AutoOntologyModelDocument` accepted the synthetic example: two terms, three attributes.
- The real file chooser imported the native JSON; all five claims began unreviewed. The actual Designer loaded the projection, edited a definition and sent it back. An explicit synthetic review made one claim eligible. A later edit returned it to `needs_review` while preserving its decision.
- After restarting the final server and refreshing the built editor, the saved definition and history remained. The real property-description textarea also updated the submitted projection. Opening a review tab no longer discards unsent editor content.
- Browser export preserved the source text byte-for-byte against the immutable stored source and its SHA-256. The separately edited property and two term bindings remained in the envelope. The source contains synthetic public-data definitions only.
- Captured browser warning/error logs were empty for both final local tabs. Screenshots and a captured-state walkthrough are linked in [the connection guide](CONNECTION.md).
- A built wheel was installed in a separate target directory and imported from there. Its workbench, example, design resources and licenses were present. An actual loopback server from that installed package served the workbench, JavaScript, CSS, actual editor and report; an import generated five claims.

The first wheel attempt without build isolation failed because the test environment lacked setuptools; the standard isolated build succeeded. The final YAML-fixed wheel was separately installed and verified with SHA-256 `1995ed3b430e285cbf2e09020c6011dc1ef51607c8bae6ec1a34746e7c6e91da`.

Two full local runs encountered Windows error 10053 on different early-rejected POST requests. Isolated checks did not reproduce it. Tests now permit only reset/abort exceptions on early rejection and then require a strict authenticated 200 response and identical workspace state; positive flows and fully read invalid JSON still require their exact response. Unauthorized requests contain a valid import so a bypass would change state and fail. Server behavior was not changed. An unread-body connection-close explanation remains an inference, not a proven OS cause.

CI runs and merge commits are recorded on the linked PRs. The local service is single-process; this verification does not claim simultaneous multi-process writes, NVIDIA inference deployment, authentication of reviewer names or factual correctness of definitions. A new generation conservatively invalidates earlier reviews across the imported workspace.
