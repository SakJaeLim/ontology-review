# Verification record

Verified locally on Windows with Python 3.14.3 on 2026-11-03. All inputs were synthetic. This record covers the extension, not the native desktop application.

## Executed checks

| Check | Result |
| --- | --- |
| Fresh virtual environment, package build and install | Passed |
| Full suite with pytest 9.2.0 | 63 passed, 1 skipped |
| Installed CLI outside the source directory | Two final claims eligible; installed core matched source bytes |
| Four-stage demo with actual file edits and SHACL | Eligible counts 2, 1, 1, 2 |
| Stale review basis and observed change then reversal | Rejected; prior decision retained |
| Wrong target, unrelated property, executable or malformed rules | Not counted as a rule pass |
| Windows junction and four SQLite hardlink preservation cases | Passed |
| Symbolic-link fixture | Skipped because the host denied link creation privileges |
| In-app browser at a local HTTP URL | Four stages, two preserved decisions, English toggle, search and empty filter state verified |
| Browser warning and error logs | Empty at verification time |
| Screen walkthrough | Six real browser captures, 23.96-second H.264 video |

The tests include malformed JSON types and Unicode, missing or changed inputs, restart persistence, exact quotes, local path restrictions, reserved state output paths and safe HTML embedding. Independent review found four input-boundary issues during development; each was fixed and rerun before publication.

The generated HTML is self-contained. Its buttons switch stored inspection results. It does not send a review decision or edit a live source. Captures are available in [the README](README.md).

## Interface follow-up, 2026-11-03

The compact workbench keeps the same inspection JSON and decision logic. Open Props tokens and two Lucide SVGs are bundled with their complete upstream license texts.

| Check | Result |
| --- | --- |
| Full local suite after the interface change | 59 passed, 6 skipped in 56.07 seconds |
| Follow-up Windows junction and state-hardlink cases with fixture permissions | 5 passed; the symbolic-link case remains skipped |
| Distinct cases across those runs | 64 passed, 1 skipped |
| Wheel resources and renderer | All six design resources included; export from wheel matches source export byte for byte |
| Recorded demo | Eligible counts 2, 1, 1, 2; inspection JSON retained |
| Actual in-app browser, normal 1265-pixel viewport | Source mismatch, rule failure, two preserved decisions, English, search, blocked filter, empty state and keyboard disclosure checked |
| Browser layout and logs | No horizontal page overflow; no captured warnings or errors |
| UTC display | Whole seconds shown; original timestamp retained in dateTime and title |
| Scoped independent review | No blocking regression; timestamp display issue fixed and checked |

The refreshed media uses six actual captures of this interface. The 24-second video is an assembly of those captured states, not a continuous screen recording. No mobile browser or screen reader test was run for this follow-up.

The ecosystem review ran four Microsoft validation-module cases and four NVIDIA model-schema cases. These are isolated module checks, not engine deployments or retrieval benchmarks. See [the research record](research/ontology-ecosystem-review.md).

## Repeat the checks

From the standalone repository root (historically `extensions/evidence-review`):

```sh
python -m pip install ".[test]"
python -m pytest -q
python demo.py --output demo-output
```

Open `demo-output/index.html`, select each recorded stage, switch to English and search for `owner`. Select a blocked-only filter after the final approval to confirm the empty state.

The added GitHub Actions workflow schedules Windows and Ubuntu checks on Python 3.11 and 3.14. Remote CI results are separate from these local results. Its action versions follow the official [setup-python](https://github.com/actions/setup-python) and [checkout](https://github.com/actions/checkout) usage documentation inspected during development.

## Scope limits

No native LLM Wiki build, native answer-time enforcement, live LLM evaluation or production-data benchmark was run. The independent review is bounded evidence, not a whole-application security certification. Path checks protect the declared input contract; they are not an operating-system isolation boundary against a hostile concurrent process.

The local actor label is not authenticated and the SQLite history is not tamper-proof. Edits that are reversed between observations cannot be detected. [The design](DESIGN.md) describes the remaining boundaries.
