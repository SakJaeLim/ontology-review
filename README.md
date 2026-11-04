# Ontology Review

**See what needs another review when a business definition changes.**

[한국어](README.ko.md) / English

[Try it](#try-it-in-a-few-minutes) / [Watch the walkthroughs](#see-it-work) / [Development and credits](PROVENANCE.md)

## The problem

An **active customer** might mean someone who bought something in the last 90 days, or the last 30 days. The choice changes how people interpret a report.

Suppose a business owner reviews and approves the 90-day definition. Someone later changes it to 30 days. **The old approval does not mean the new wording was reviewed.** Ontology Review keeps that distinction visible.

| Action | What the tool shows |
| --- | --- |
| Review and approve “a customer who purchased in the last 90 days” | The wording that was inspected and the recorded decision. |
| Change the description to “the last 30 days” | The current wording needs another review. The earlier approval stays in history. |
| Inspect the change again | Compare the source and proposal, then record a new decision about the current version. |

**A person decides whether 30 or 90 days is right.** The tool records what was reviewed and shows when a later change needs attention. It does not calculate customer counts or update a company database.

The active-customer example explains the intended use. The screens and videos below use a separate bundled synthetic dictionary.

## When it helps

This is for data consultants agreeing on terminology with a client, or data stewards maintaining a dictionary: **people who revise definitions and review them repeatedly.** A data dictionary is a file describing what terms and fields mean.

The review screen brings together the original wording, the proposal and earlier decisions. The intended benefit is to **reduce the chance of treating changed wording as already reviewed**. Time savings and customer outcomes have not yet been measured.

A document or spreadsheet may be simpler for a short glossary written once. This release is a prototype for one person working locally. It does not yet provide staff accounts or shared organizational workflows.

## What was built

The project connects an existing editor to a workflow for **keeping the source, comparing a proposal, recording a decision and requiring review after a change**.

- Preserve the imported file and keep edited descriptions separately.
- Show the source and proposal together and retain earlier decisions.
- Reassess review status after approved content changes.
- Provide the local server, tests and demonstrations for that workflow.

The visual editor comes from Microsoft. The input format comes from NVIDIA. **This project's contribution is the connection and review functionality between them.** It runs without LLM Wiki. [Development history and credits](PROVENANCE.md)

The current ontology scope is **descriptions attached to existing terms and properties**. Designing new relationships and structures, or automatically building an ontology from company documents, remains outside this release.

## See it work

The screen compares the original on the left with the proposal on the right. **‘재검토 필요’ means ‘needs review’:** the current content needs another decision.

![Ontology Review comparing the source and proposed definition after a later edit requires review](assets/standalone-review.png)

**Dictionary editing and review in 20 seconds**

Import, edit in Microsoft Designer, review, then edit again to see the decision become stale.

https://github.com/user-attachments/assets/a4a60191-5f28-4309-bd0a-af84d0a279a1

[Download the MP4](assets/connection-walkthrough.mp4)

<details>
<summary>Watch source and rule changes trigger a new review (24 seconds)</summary>

https://github.com/user-attachments/assets/6e8241bc-d95f-42e9-82f7-452eb29e97d0

[Download the MP4](assets/walkthrough.mp4). The earlier decision stays in history while a changed source or failed rule requires another review.

</details>

These videos assemble actual browser captures. They are not continuous screen recordings. Captures from the earlier extension retain its original branding; the same engine now lives in this independent repository. [Media details](MEDIA.md).

<details>
<summary>More actual screens</summary>

![Import a native dictionary](assets/connection-import.jpg)
![An explicitly accepted definition](assets/connection-approved.jpg)
![Inspect an exact quotation and local rule result](assets/evidence.jpg)
![Earlier decisions remain in history](assets/history.jpg)
![English inspection report](assets/english.jpg)

</details>

## Try it in a few minutes

**There are two ways to try it.** The commands below execute the example and generate a report of its recorded review steps. To edit descriptions and submit decisions yourself, follow the [live editor guide](CONNECTION.md). Input currently requires NVIDIA's JSON/YAML format; ordinary Excel and PDF files are not directly supported.

The recorded demo needs **Python 3.11+**. It does not need the Microsoft editor, a running LLM Wiki, an API key or a model server. Installation downloads Python dependencies; the demonstration then runs locally.

```sh
git clone https://github.com/SakJaeLim/ontology-review.git
cd ontology-review
```

**Windows PowerShell**

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install .
.venv\Scripts\python demo.py --output demo-output
```

**macOS and Linux**

```sh
python3 -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/python demo.py --output demo-output
```

Open `demo-output/index.html` in a browser, or `index.en.html` for English. The four stages are real stored executions with expected eligible-claim counts of **2 → 1 → 1 → 2**. Buttons inspect those records; they do not edit a live workspace. Use a new output directory for another run.

For **live dictionary editing**, follow the [Windows, macOS and Linux connection guide](CONNECTION.md). It builds a pinned version of the Microsoft fork separately and mounts it on the local review server. Node.js is needed for that editor build.

<details>
<summary>Developer details: features, commands, limits and checks</summary>

## What is implemented

| Part | Behavior |
| --- | --- |
| Dictionary adapter | Imports native NVIDIA Auto Ontology JSON or safe YAML; preserves exact UTF-8 input and its hash. |
| Editor connection | Binds existing terms and attributes to the Microsoft Designer; accepts description edits with a workspace revision check. |
| Review engine | Records explicit decisions against the inspected basis. Observed changes, including a change and reversal, require new review. |
| Local rules | Checks exact quotations and a bounded, non-executable subset of SHACL constraints. |
| Review history | Keeps observations and decisions in SQLite across restarts. |
| Inspection report | Self-contained HTML with Korean and English, filtering, source locations and decision history. |
| Export | Includes the original dictionary, edited projection and bindings. It is not an automatically rewritten NVIDIA model. |

The live workbench is currently Korean; the inspection report and these guides support Korean and English.

## Inspect your own source-bound claims

Start with [the synthetic manifest](examples/synthetic/workspace.json). Declare exact quoted lines, local Turtle rules and the names of pages that depend on each claim.

```sh
python -m evidence_wiki inspect PATH_TO_WORKSPACE --json inspection.json --html inspection.html
python -m evidence_wiki review PATH_TO_WORKSPACE CLAIM_ID accept --basis BASIS_FROM_INSPECTION --actor REVIEWER_NAME
```

Use the Python executable from your virtual environment. The installed `ontology-review` command is equivalent; `evidence-wiki` remains as a compatibility alias. The Python import name stays `evidence_wiki` so existing scripts continue to work.

A factlog CSV importer creates unreviewed drafts. It does not transfer an upstream “accepted” flag into a source-bound approval. [State model and input contract](DESIGN.md).

## What this project contributes

This repository owns the Python review engine, dictionary adapter, local server, inspection UI, tests and synthetic examples. The **visual ontology editor is Microsoft's work**; the [connected fork](https://github.com/SakJaeLim/Ontology-Playground) contains the additional connection panel and draft-binding changes.

The code originated in `extensions/evidence-review` of an LLM Wiki fork. Its three feature commits were extracted with Git subtree history. **LLM Wiki is not a runtime dependency.** Native wiki approvals and answers are not intercepted. NVIDIA contributes the dictionary format; its inference service is not deployed here.

[Contribution map, exact revisions and credits](PROVENANCE.md). Moving this code does not imply an accepted contribution to any upstream project.

## Current limits

- The live adapter edits existing descriptions and ontology title/description. It rejects structural edits, renaming and reordering of bound properties.
- One workspace supports one server process, with at most 200 reviewable definitions and a 1 MiB dictionary.
- Reviewer names are local labels, not authenticated identities. There is no multi-user access control or tamper-proof audit store.
- Checks establish source alignment and rule conformance, not factual truth or semantic equivalence.
- Source and rule changes are observed when inspected. Changes reversed between inspections are not detectable. File-level invalidation is conservative.
- There is no Foundry connector, enterprise data pipeline, native wiki answer guard or automatic semantic impact analysis.

## Reproduce the checks

```sh
python -m pip install ".[test]"
python -m pytest -q
python -m pip wheel . --no-deps --wheel-dir dist
python scripts/check_wheel.py dist
python scripts/check_docs.py
```

[CI](https://github.com/SakJaeLim/ontology-review/actions/workflows/ci.yml) runs the core tests, demo and package checks on Windows, macOS and Linux with Python 3.11 and 3.14. The actual results and browser scope are recorded in [standalone verification](STANDALONE_VERIFICATION.md); the historical [engine](VERIFICATION.md) and [connection](CONNECTION_VERIFICATION.md) records remain available.

</details>

The core program and installable package are checked in CI on Windows, macOS and Linux. The connected Microsoft editor was exercised in an actual browser on Windows. [Verification record](STANDALONE_VERIFICATION.md)

## License

[GPL-3.0-only](LICENSE). Existing notices and attribution are retained in [NOTICE.md](NOTICE.md). Bundled Open Props and Lucide assets retain their own licenses in [third-party notices](THIRD_PARTY_NOTICES.md). The Microsoft editor is built separately under its own license.
