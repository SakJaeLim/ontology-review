# Evidence Review for LLM Wiki

[한국어](README.ko.md) / English

**When evidence changes, review it again.**

A small offline extension for examining claims, source revisions and local ontology constraints. It preserves earlier decisions and shows which declared wiki pages need attention after a source or rule changes.

This is an experimental extension in [SakJaeLim's LLM Wiki fork](https://github.com/SakJaeLim/llm_wiki), built on [nashsu/llm_wiki](https://github.com/nashsu/llm_wiki). The desktop app and its existing features are upstream work. This extension has its own Python workspace; it does not intercept the desktop app's answers or change its native approval records.

![Source revisions, rule checks and review decisions](assets/architecture.svg)

## Captured in the in-app browser

[![Open the 24-second captured-state walkthrough](assets/overview.jpg)](assets/walkthrough.mp4)

[Watch the walkthrough](assets/walkthrough.mp4). It combines six actual browser captures from the recorded demo. The HTML lets you inspect each stage, switch languages and filter claims yourself.

<details>
<summary>Evidence, history and English view</summary>

![The current quotation and local rule result](assets/evidence.jpg)
![Both review decisions remain in history](assets/history.jpg)
![English interface](assets/english.jpg)

</details>

## Run the recorded demo

Python 3.11 or newer is required. From this directory:

```sh
python -m pip install ".[test]"
python demo.py --output demo-output
python -m pytest -q
```

The demo uses synthetic documents. It performs real file edits, SHACL validation and review decisions, then exports an interactive HTML record. No LLM, API key or paid service is required. Package installation requires access to the Python package registry; the demo itself runs locally.

Use a new or empty destination. The demo refuses to overwrite an existing run. Open `demo-output/index.html` in a browser, or `index.en.html` for English. Stage buttons show stored executions, not live edits to a workspace.

| Stage | What happens | Expected result |
| --- | --- | --- |
| Initial review | Two independent claims receive explicit demo reviews | Both are eligible in this inspector |
| Source edit | The retention source changes from 30 to 90 days | The old 30-day claim needs review |
| Claim revision | The claim and quotation change to 90 days; the limit remains 60 | The quote matches, but the rule fails |
| Rule revision and review | The demo limit changes to 120 and a new review is recorded | The current claim is eligible; history remains |

The unrelated team claim stays eligible throughout. The retention numbers are invented examples, not legal guidance.

## Inspect a workspace

Copy the manifest and input layout from the demo or `examples/`. Declare a claim's exact quoted lines, local `.ttl` rule files and affected page names in `workspace.json`.

```sh
python -m evidence_wiki inspect PATH_TO_WORKSPACE --json inspection.json --html inspection.html
python -m evidence_wiki review PATH_TO_WORKSPACE CLAIM_ID accept --basis BASIS_FROM_INSPECTION --actor REVIEWER_NAME
```

Report paths are relative to that workspace. A review checks the current inputs again and rejects an outdated basis. It cannot accept a claim while an evidence or rule check fails. Reviewer names are local labels, not authenticated identities.

The optional factlog CSV importer produces draft claims for manual binding:

```sh
python -m evidence_wiki import-factlog PATH_TO_WORKSPACE claims.csv --out drafts.json
```

It does not turn an upstream accepted row into an evidence-bound approval. Add exact quotations and applicable rules before review.

## What is checked

- Source content hashes and observed revisions, including an observed change and reversal.
- Exact text at an inclusive line range, with line endings normalized.
- A bounded subset of local SHACL property constraints through `pyshacl`.
- Review basis changes, missing inputs and declared affected wiki pages.
- Workspace path boundaries and unsafe rule constructs.

SHACL conformance is a structural check, not proof that the source or claim is true. A changed file conservatively affects every claim bound to it. This is not semantic change propagation.

## Boundaries and next contributions

The report is a dated snapshot. It does not watch files, authenticate reviewers or provide a tamper-proof audit log. It cannot detect a source that changed and reverted between inspections. Only manifest-declared dependencies are covered.

Native LLM Wiki integration, an answer-time guard, richer SHACL support and an [OntoRipple](https://github.com/oeg-upm/OntoRipple) adapter are follow-up work. No upstream contribution has been merged as part of this extension.

See [the executed checks](VERIFICATION.md) and [the design and input boundaries](DESIGN.md) for the evidence, state model and upstream credits. This extension follows the repository's [GPL-3.0 license](../../LICENSE).
