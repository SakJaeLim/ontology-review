# Evidence review design

[English guide](README.md) / [한국어 안내](README.ko.md)

## The problem

An approval records a decision about the evidence available at that time. A file at the same path can later contain different text. The historical decision should remain visible, while the current claim needs another review.

Ontology Review owns its workspace and review history. It runs independently of LLM Wiki and does not alter the desktop application's native review store or answer pipeline.

## State and ownership

The workspace manifest declares claims, quoted line ranges, local Turtle rule files and affected wiki page names. SQLite stores observations and decisions. JSON and HTML are derived inspection reports.

Each decision binds to a claim basis that includes its definition and observed source and rule revisions. Content hashes alone are insufficient: after an observed A to B to A change, the restored content must not silently regain its old approval. An observation revision distinguishes that sequence.

An inspection re-reads inputs. An explicit review must present the basis it inspected; a stale basis cannot approve a later revision. Decisions remain in history across restarts. Eligibility is a current assessment by this extension, not a rewrite of historical approval.

## Validation means different things

1. A quote check establishes whether the declared line range matches the supplied text.
2. A source observation establishes which local file revision was inspected.
3. SHACL checks a claim graph against the supported local constraints.
4. A review records a named actor's decision about that basis.

None of these proves that a source is factually correct. A rule that permits 120 days may be inappropriate even when a 90-day claim conforms to it. The demo changes this rule to illustrate versioning, not to recommend a retention policy.

Every rule file is checked in full against the supported safe profile. Validation then uses only property constraints whose shape targets the current claim's subject and whose direct path matches its predicate. Other subjects and properties need their own claims and checks. A shared rule file does not establish conformance of a complete multi-property entity. Malformed or unsupported constructs anywhere in the file still make the rule not checked. This scope is part of the versioned review policy, so earlier approvals require review after it changes.

The standalone JSON inspection preserves Python integer values. The HTML display copy encodes integers outside JavaScript's safe range as decimal strings, retaining the declared RDF datatype. This prevents rounding in the visible claim and search without changing the source inspection, claim or review basis.

## Deliberate limits

- Checks cover declared dependencies, not every page or claim in a native wiki.
- Changes anywhere in a declared file conservatively invalidate claims bound to that file. This is not semantic, term-level impact analysis.
- An edit and reversal between observations cannot be detected.
- The HTML report shows a stored inspection time. It does not watch files or submit approvals.
- The actor name is an attribution label, not authenticated identity. Local SQLite is not a tamper-proof audit store.
- Only a small, non-executable SHACL subset is supported. Unsupported constructs must fail closed instead of being ignored.
- Remote resources, imports, SPARQL constraints and JavaScript rules are outside this extension's input contract.
- No native answer guard, document parser, automatic ontology induction or OntoRipple runtime integration is included.

## Why it began as a separate extension

The upstream factlog reproduction used its actual merge and compilation commands with synthetic input. A source changed from 30 to 90 days at the same path; the prior 30-day accepted fact remained in the compiled input. The reproduction did not run an LLM or a Datalog answer query, so it does not establish that every downstream answer is wrong.

Changing one merge condition would not cover independent readers of compiled accepted facts. The first slice therefore makes evidence drift visible with its own state owner. Native enforcement remains a separate integration task that must inventory every consumer.

## Upstream credit and contribution targets

[nashsu/llm_wiki](https://github.com/nashsu/llm_wiki) is the original desktop wiki. Its source traceability and asynchronous review features remain upstream work. The Python component began in a fork and now has its own repository, retaining GPL-3.0-only. The desktop application is not a runtime dependency. See [provenance](PROVENANCE.md) for the extracted history and exact contribution boundaries.

[semantic-reasoning/factlog](https://github.com/semantic-reasoning/factlog) informed the source-version boundary. No claim of a merged upstream fix is made.

[oeg-upm/OntoRipple](https://github.com/oeg-upm/OntoRipple) already implements ontology-change propagation to mappings and constraints. Two upstream deprecation-reversal fixtures were run separately during research. OntoRipple is a future adapter candidate, not a dependency of this extension.

Useful follow-ups are an adapter for native LLM Wiki review items, a complete factlog source-version binding proposal, and an OntoRipple adapter that records the resulting rule revision before review. Each needs its own end-to-end verification.
