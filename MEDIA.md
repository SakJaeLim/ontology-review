# Screens and walkthroughs

All photographs of the interface are actual browser captures using synthetic data. No customer records or private research documents are included.

| File | Content |
| --- | --- |
| `assets/review-flow.png` | Generated explanatory flowchart: a 90-day definition is approved, changed to 30 days, and reviewed again while history is retained. Korean labels with English subtitles. |
| `assets/system-architecture.png` | Generated architecture diagram showing the local file input, this project's review service, the Microsoft editor and stored outputs. Korean labels with English subtitles. |
| `assets/standalone-review.png` | Fresh standalone-package capture on 2026-11-04: original and edited definitions with the new review requirement. |
| `assets/connection-walkthrough.mp4` | About 20 seconds; four captured states: dictionary import, Microsoft editing, approval, and a later edit requiring review. |
| `assets/walkthrough.mp4` | About 24 seconds; six captured states showing source/rule changes, review history and English reporting. |
| `assets/connection-*.jpg` | The corresponding live dictionary workflow screens. |
| `assets/overview.jpg`, `evidence.jpg`, `history.jpg`, `english.jpg` | Inspector screens from the recorded synthetic workflow. |
| `assets/architecture.svg` | Original explanatory diagram of source revisions and review basis. |

The MP4 files assemble still captures; they are not uninterrupted screen recordings. The earlier LLM Wiki extension label remains visible in the original recordings. Those assets are retained unmodified to preserve what was actually observed.

Both README language versions embed copies uploaded to GitHub's media attachment service so visitors can play them in the page. The original MP4 files remain tracked in `assets/` and are linked below each player for download. The attachment URLs are presentation copies, not runtime dependencies.

The standalone repository contains the same review engine and separately records its own verification in STANDALONE_VERIFICATION.md. New standalone screenshots are identified there.

The media inventory with SHA-256 values is in [assets/media-manifest.json](assets/media-manifest.json). These hashes document file preservation, not software correctness.

The two new PNG diagrams explain the documented behavior; they are not captured application screens or evidence of a customer deployment. They were created with the built-in image generation tool. The [generation prompts](assets/diagram-prompts.md) are retained for future revisions. Their labels and arrow directions were checked against the connection code and documentation before publication.
