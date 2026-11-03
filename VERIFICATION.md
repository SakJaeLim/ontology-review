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

## Repeat the checks

From `extensions/evidence-review`:

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
