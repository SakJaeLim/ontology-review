# Standalone verification

This record distinguishes the extracted component from its original host and external editor. The current extraction is based on `a3527442f440d1521e111a9c7f0328fa66efe248` of SakJaeLim/llm_wiki. The integrated Microsoft editor is pinned to `40005215fc283e4abf1c5abae0ca0f9053a87cf8`.

## Local verification on 2026-11-04

Windows, Python 3.14.3, fresh virtual environment. All inputs were synthetic.

| Check | Observed result |
| --- | --- |
| Git subtree extraction | Extracted tree and original component tree both `452c898ad7cbbbb6f3e5a81e07baa9885dd82261`; three component commits retained. |
| Full Python suite | 138 passed, 1 skipped in 38.85 seconds. The Windows symbolic-link fixture was unavailable. |
| Recorded demo | Eligible counts 2, 1, 1, 2 across four actual file/review stages. |
| Wheel installation outside the checkout | Module path, version, both CLI entry points, web assets and license files verified. |
| Installed service in the in-app browser | New workspace on port 8771; loaded five synthetic definitions, edited a description in the actual Microsoft fork, saved, accepted, edited again and observed `needs_review` with the earlier decision retained. |
| Standalone screenshot | `assets/standalone-review.png`, captured from the installed service after the second edit. |
| Media preservation | All eleven inherited image/video/diagram files retained byte-for-byte; the fresh screenshot is additional. |

The historical records remain in VERIFICATION.md and CONNECTION_VERIFICATION.md. The connected Microsoft build was the previously verified, pinned build; this extraction does not change its code.

The new CI matrix includes Windows, macOS and Ubuntu with Python 3.11 and 3.14. This validates the Python component, HTTP tests, offline demo and package resources. It does not exercise the full Microsoft editor in a browser on every operating system.

All demonstrations use synthetic data. No customer outcome, full NVIDIA inference deployment, native LLM Wiki interception or Foundry connection is claimed.
