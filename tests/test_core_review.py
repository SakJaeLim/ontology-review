import csv
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from demo import run_demo
from evidence_wiki import EvidenceError, EvidenceWorkspace
from evidence_wiki import rules
from evidence_wiki.inputs import MAX_FILE_BYTES, import_factlog


EXTENSION = Path(__file__).resolve().parents[1]
FIXTURE = EXTENSION / "examples" / "synthetic"


@pytest.fixture
def root(tmp_path):
    destination = tmp_path / "workspace"
    shutil.copytree(FIXTURE, destination)
    return destination


def edit_manifest(root, edit):
    path = root / "workspace.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    edit(manifest)
    path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")


def claim(workspace, claim_id="retention"):
    return next(item for item in workspace.inspect()["claims"] if item["id"] == claim_id)


def accept(workspace, claim_id="retention"):
    current = claim(workspace, claim_id)
    workspace.review(claim_id, "accept", basis=current["basis"], actor="Test reviewer")
    return claim(workspace, claim_id)


def test_first_inspection_requires_human_review(root):
    current = claim(EvidenceWorkspace.open(root))
    assert current["review_state"] == "unreviewed"
    assert current["eligibility"] == "unreviewed"
    assert current["evidence"][0]["actual_text"] == "SyntheticProject retains records for 30 days."
    assert current["evidence"][0]["status"] == "matches"
    assert current["rules"][0]["status"] == "conforms"
    assert current["rules"][0]["focus_count"] == 1


def test_approval_and_repeated_inspections_persist_across_restart(root):
    workspace = EvidenceWorkspace.open(root)
    approved = accept(workspace)
    again = claim(EvidenceWorkspace.open(root))
    assert approved == again
    assert approved["eligibility"] == "eligible"
    workspace.review("retention", "accept", basis=approved["basis"], actor="Test reviewer")
    assert claim(workspace)["decisions"] == approved["decisions"]


def test_source_edit_only_invalidates_dependants(root):
    workspace = EvidenceWorkspace.open(root)
    old = accept(workspace)
    other = accept(workspace, "owner")
    (root / "sources/retention.md").write_text("# Changed\n\nSyntheticProject retains records for 90 days.\n", encoding="utf-8")
    report = EvidenceWorkspace.open(root).inspect()
    changed = report["claims"][0]
    assert changed["review_state"] == "needs_review"
    assert changed["eligibility"] == "blocked"
    assert changed["decisions"] == old["decisions"]
    assert changed["evidence"][0]["digest"] != old["evidence"][0]["digest"]
    assert changed["evidence"][0]["revision"] > old["evidence"][0]["revision"]
    assert report["claims"][1] == other
    assert report["affected_pages"] == ["wiki/retention.md"]


def test_stale_review_commits_observation_but_no_decision_and_no_revival(root):
    workspace = EvidenceWorkspace.open(root)
    approved = accept(workspace)
    path = root / "sources/retention.md"
    original = path.read_bytes()
    path.write_bytes(original + b"\nUnrelated note.\n")
    with pytest.raises(EvidenceError, match="changed") as raised:
        workspace.review("retention", "accept", basis=approved["basis"], actor="Test reviewer")
    assert raised.value.code == "stale_basis"
    path.write_bytes(original)
    current = claim(EvidenceWorkspace.open(root))
    assert current["review_state"] == "needs_review"
    assert current["evidence"][0]["digest"] == approved["evidence"][0]["digest"]
    assert current["evidence"][0]["revision"] > approved["evidence"][0]["revision"]
    assert current["decisions"] == approved["decisions"]


def test_claim_tamper_invalidates_even_if_rules_still_conform(root):
    workspace = EvidenceWorkspace.open(root)
    previous = accept(workspace)
    edit_manifest(root, lambda m: m["claims"][0].update(value=31))
    current = claim(workspace)
    assert current["rules"][0]["status"] == "conforms"
    assert current["basis"] != previous["basis"]
    assert current["eligibility"] == "blocked"
    assert current["review_state"] == "needs_review"


def test_removed_claim_cannot_revive_approval_when_readded(root):
    workspace = EvidenceWorkspace.open(root)
    approved = accept(workspace)
    original = (root / "workspace.json").read_bytes()
    edit_manifest(root, lambda m: m["claims"].pop(0))
    assert [c["id"] for c in workspace.inspect()["claims"]] == ["owner"]
    (root / "workspace.json").write_bytes(original)
    current = claim(workspace)
    assert current["review_state"] == "needs_review"
    assert current["decisions"] == approved["decisions"]


def test_missing_source_and_reappearance_require_review(root):
    workspace = EvidenceWorkspace.open(root)
    approved = accept(workspace)
    path = root / "sources/retention.md"
    original = path.read_bytes()
    path.unlink()
    missing = claim(workspace)
    assert missing["evidence"][0]["availability"] == "missing"
    assert missing["evidence"][0]["actual_text"] is None
    assert missing["eligibility"] == "blocked"
    path.write_bytes(original)
    current = claim(workspace)
    assert current["eligibility"] == "blocked"
    assert current["basis"] != approved["basis"]


def test_rule_drift_and_policy_revision_invalidate_approval(root, monkeypatch):
    workspace = EvidenceWorkspace.open(root)
    approved = accept(workspace)
    rule = root / "rules/retention.ttl"
    rule.write_bytes(rule.read_bytes() + b"\n# Documentation changes also require re-review.\n")
    current = claim(workspace)
    assert current["rules"][0]["status"] == "conforms"
    assert current["basis"] != approved["basis"]
    assert current["review_state"] == "needs_review"
    approved = accept(workspace)
    monkeypatch.setattr(rules, "POLICY_REVISION", "next-validation-policy")
    assert claim(workspace)["basis"] != approved["basis"]
    assert claim(workspace)["eligibility"] == "blocked"


def test_rejection_is_distinct_and_retained(root):
    workspace = EvidenceWorkspace.open(root)
    before = claim(workspace)
    workspace.review("retention", "reject", basis=before["basis"], actor="Reviewer A")
    rejected = claim(EvidenceWorkspace.open(root))
    assert rejected["review_state"] == "rejected"
    assert rejected["eligibility"] == "blocked"
    approved = accept(workspace)
    assert [d["action"] for d in approved["decisions"]] == ["reject", "accept"]
    assert approved["eligibility"] == "eligible"


@pytest.mark.parametrize("actor", ["", " ", None, "x" * 201])
def test_accept_requires_named_reviewer(root, actor):
    workspace = EvidenceWorkspace.open(root)
    with pytest.raises(EvidenceError) as raised:
        workspace.review("retention", "accept", basis=claim(workspace)["basis"], actor=actor)
    assert raised.value.code == "invalid_actor"
    assert claim(workspace)["decisions"] == []


def test_real_shacl_violation_cannot_be_accepted(root):
    workspace = EvidenceWorkspace.open(root)
    edit_manifest(root, lambda m: m["claims"][0].update(value=90))
    current = claim(workspace)
    assert current["rules"][0]["status"] == "violates"
    assert current["rules"][0]["focus_count"] == 1
    assert current["rules"][0]["messages"]
    with pytest.raises(EvidenceError) as raised:
        workspace.review("retention", "accept", basis=current["basis"], actor="Reviewer")
    assert raised.value.code == "checks_failed"


@pytest.mark.parametrize("shared_node", [False, True])
def test_shared_rule_file_checks_only_the_claim_property(root, shared_node):
    retention = (root / "rules/retention.ttl").read_text(encoding="utf-8")
    owner = (root / "rules/owner.ttl").read_text(encoding="utf-8")
    if shared_node:
        owner = owner.replace("demo:OwnerShape", "demo:RetentionShape")
    (root / "rules/shared.ttl").write_text(retention + "\n" + owner, encoding="utf-8")
    edit_manifest(root, lambda m: [item.update(rules=["rules/shared.ttl"]) for item in m["claims"]])
    workspace = EvidenceWorkspace.open(root)
    report = workspace.inspect()
    assert [item["rules"][0]["status"] for item in report["claims"]] == ["conforms", "conforms"]
    assert accept(workspace)["eligibility"] == "eligible"
    assert accept(workspace, "owner")["eligibility"] == "eligible"
    edit_manifest(root, lambda m: m["claims"][0].update(value=90))
    report = workspace.inspect()
    assert [item["rules"][0]["status"] for item in report["claims"]] == ["violates", "conforms"]


def test_shared_rule_targets_do_not_require_unrelated_subject_triples(root):
    path = root / "rules/retention.ttl"
    path.write_text(path.read_text(encoding="utf-8").replace(
        "sh:targetNode demo:project", "sh:targetNode demo:project, demo:other"), encoding="utf-8")
    current = claim(EvidenceWorkspace.open(root))
    assert current["rules"][0]["status"] == "conforms"
    assert current["rules"][0]["focus_count"] == 1


def test_every_relevant_constraint_remains_active(root):
    path = root / "rules/retention.ttl"
    second = path.read_text(encoding="utf-8").replace("demo:RetentionShape", "demo:StricterShape").replace("sh:maxInclusive 60", "sh:maxInclusive 20")
    path.write_text(path.read_text(encoding="utf-8") + "\n" + second, encoding="utf-8")
    current = claim(EvidenceWorkspace.open(root))
    assert current["rules"][0]["status"] == "violates"
    assert current["eligibility"] == "blocked"


def test_unrelated_unsafe_shape_still_rejects_the_whole_rule_file(root):
    path = root / "rules/retention.ttl"
    owner = (root / "rules/owner.ttl").read_text(encoding="utf-8")
    owner += "\ndemo:OwnerShape sh:sparql [] .\n"
    path.write_text(path.read_text(encoding="utf-8") + "\n" + owner, encoding="utf-8")
    current = claim(EvidenceWorkspace.open(root))
    assert current["rules"][0]["status"] == "not_checked"
    assert current["eligibility"] == "blocked"


@pytest.mark.parametrize("old,new", [("sh:targetNode demo:project", "sh:targetNode demo:other"),
                                       ("sh:path demo:retentionDays", "sh:path demo:other")])
def test_zero_relevant_focus_is_not_checked(root, old, new):
    path = root / "rules/retention.ttl"
    path.write_text(path.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")
    current = claim(EvidenceWorkspace.open(root))
    assert current["rules"][0]["status"] == "not_checked"
    assert current["rules"][0]["focus_count"] == 0
    assert current["eligibility"] == "blocked"


@pytest.mark.parametrize("extra", [
    "<urn:demo:RetentionShape> <http://www.w3.org/ns/shacl#sparql> [] .",
    "<urn:demo:RetentionShape> <http://www.w3.org/2002/07/owl#imports> <https://example.invalid/remote> .",
    "<urn:demo:RetentionShape> <http://www.w3.org/ns/shacl#js> [] .",
    "<urn:demo:RetentionShape> <http://www.w3.org/ns/shacl#rule> [] .",
    "<urn:demo:RetentionShape> <http://www.w3.org/ns/shacl#expression> [] .",
])
def test_executable_or_external_rule_constructs_are_rejected(root, extra):
    path = root / "rules/retention.ttl"
    path.write_text(path.read_text(encoding="utf-8") + "\n" + extra, encoding="utf-8")
    current = claim(EvidenceWorkspace.open(root))
    assert current["rules"][0]["status"] == "not_checked"
    assert "Unsupported" in current["rules"][0]["messages"][0]
    assert current["eligibility"] == "blocked"


@pytest.mark.parametrize("content", ["", "this is not turtle", "@prefix sh: <http://www.w3.org/ns/shacl#> ."])
def test_empty_and_malformed_rules_do_not_pass(root, content):
    (root / "rules/retention.ttl").write_text(content, encoding="utf-8")
    current = claim(EvidenceWorkspace.open(root))
    assert current["rules"][0]["status"] == "not_checked"
    assert current["eligibility"] == "blocked"


def test_bad_declared_datatype_is_blocked_even_without_shacl_datatype(root):
    path = root / "rules/retention.ttl"
    path.write_text(path.read_text(encoding="utf-8").replace("sh:datatype xsd:integer ;", "").replace("sh:minInclusive 1 ; sh:maxInclusive 60", "sh:minLength 1"), encoding="utf-8")
    edit_manifest(root, lambda m: m["claims"][0].update(value="not-an-integer"))
    workspace = EvidenceWorkspace.open(root)
    current = claim(workspace)
    assert "invalid_claim_value" in current["reason_codes"]
    assert current["eligibility"] == "blocked"
    with pytest.raises(EvidenceError) as raised:
        workspace.review("retention", "accept", basis=current["basis"], actor="Reviewer")
    assert raised.value.code == "checks_failed"


@pytest.mark.parametrize("path", ["../outside.md", "/outside.md", "C:/outside.md", "https://example.invalid/secret",
                                  "sources/../retention.md", "sources\\retention.md", "sources/CON", "sources/a:stream"])
def test_unsafe_evidence_paths_are_never_read(root, path):
    edit_manifest(root, lambda m: m["claims"][0]["evidence"][0].update(path=path))
    current = claim(EvidenceWorkspace.open(root))
    assert current["evidence"][0]["availability"] == "unsafe"
    assert current["evidence"][0]["actual_text"] is None
    assert current["evidence"][0]["digest"] is None
    assert current["eligibility"] == "blocked"


def test_symlink_escape_is_never_read(root, tmp_path):
    outside = tmp_path / "outside.md"
    outside.write_text("secret", encoding="utf-8")
    link = root / "sources/linked.md"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("Creating symbolic links requires platform permission.")
    edit_manifest(root, lambda m: m["claims"][0]["evidence"][0].update(path="sources/linked.md"))
    current = claim(EvidenceWorkspace.open(root))
    assert current["evidence"][0]["availability"] == "unsafe"
    assert current["evidence"][0]["actual_text"] is None


@pytest.mark.skipif(os.name != "nt", reason="Windows junction regression")
def test_windows_junction_escape_is_never_read(root, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.md").write_text("secret", encoding="utf-8")
    link = root / "linked"
    command = "New-Item -ItemType Junction -Path '" + str(link).replace("'", "''") + "' -Target '" + str(outside).replace("'", "''") + "' | Out-Null"
    result = subprocess.run(["powershell", "-NoProfile", "-Command", command], capture_output=True, text=True)
    if result.returncode:
        pytest.skip("The platform denied creation of the junction fixture.")
    edit_manifest(root, lambda m: m["claims"][0]["evidence"][0].update(path="linked/secret.md"))
    current = claim(EvidenceWorkspace.open(root))
    assert current["evidence"][0]["availability"] == "unsafe"
    assert current["evidence"][0]["actual_text"] is None


@pytest.mark.parametrize("suffix", ["", "-journal", "-wal", "-shm"])
def test_state_hardlinks_are_rejected_without_touching_their_target(root, tmp_path, suffix):
    outside = tmp_path / "outside-state"
    outside.write_bytes(b"Sentinel content outside the review workspace.")
    state = root / ".evidence-review"
    state.mkdir()
    try:
        os.link(outside, state / ("state.sqlite3" + suffix))
    except OSError:
        pytest.skip("The platform denied creation of the hardlink fixture.")
    original = outside.read_bytes()
    with pytest.raises(EvidenceError) as raised:
        EvidenceWorkspace.open(root)
    assert raised.value.code == "unsafe_state"
    assert outside.read_bytes() == original


def test_reads_are_bounded_and_invalid_encoding_fails_closed(root):
    workspace = EvidenceWorkspace.open(root)
    source = root / "sources/retention.md"
    source.write_bytes(b"x" * (MAX_FILE_BYTES + 1))
    assert claim(workspace)["evidence"][0]["availability"] == "too_large"
    source.write_bytes(b"\xff\xfe")
    current = claim(workspace)
    assert current["evidence"][0]["status"] == "invalid_encoding"
    assert current["eligibility"] == "blocked"


def test_quotes_use_exact_inclusive_spans_and_no_relocation(root):
    workspace = EvidenceWorkspace.open(root)
    source = root / "sources/retention.md"
    original = source.read_text(encoding="utf-8")
    source.write_bytes(original.replace("\n", "\r\n").encode("utf-8"))
    assert claim(workspace)["evidence"][0]["status"] == "matches"
    source.write_text("Inserted line\n" + original, encoding="utf-8")
    assert claim(workspace)["evidence"][0]["status"] == "mismatch"
    edit_manifest(root, lambda m: m["claims"][0]["evidence"][0].update(start_line=100, end_line=100))
    assert claim(workspace)["evidence"][0]["status"] == "span_missing"


@pytest.mark.parametrize("content", ["{", '{"schema_version":1,"schema_version":1,"claims":[]}',
                                     '{"schema_version":true,"claims":[]}', '{"schema_version":1,"claims":{}}',
                                     '{"schema_version":1,"claims":[{}]}'])
def test_malformed_manifests_fail_explicitly(root, content):
    (root / "workspace.json").write_text(content, encoding="utf-8")
    with pytest.raises(EvidenceError) as raised:
        EvidenceWorkspace.open(root).inspect()
    assert raised.value.code == "invalid_manifest"


@pytest.mark.parametrize("datatype", [[], {}, None])
def test_non_scalar_datatype_is_a_structured_manifest_error(root, datatype):
    edit_manifest(root, lambda m: m["claims"][0].update(datatype=datatype))
    result = subprocess.run([sys.executable, "-B", "-m", "evidence_wiki", "inspect", str(root)],
                            cwd=EXTENSION, capture_output=True, text=True, encoding="utf-8")
    assert result.returncode == 2
    assert json.loads(result.stderr)["error"] == "invalid_manifest"


def test_unpaired_unicode_surrogate_is_a_structured_manifest_error(root):
    path = root / "workspace.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["claims"][0]["title"] = "\ud800"
    path.write_text(json.dumps(manifest, ensure_ascii=True), encoding="utf-8")
    result = subprocess.run([sys.executable, "-B", "-m", "evidence_wiki", "inspect", str(root)],
                            cwd=EXTENSION, capture_output=True, text=True, encoding="utf-8")
    assert result.returncode == 2
    assert json.loads(result.stderr)["error"] == "invalid_manifest"


def test_malformed_numeric_rule_bound_is_not_checked(root):
    path = root / "rules/retention.ttl"
    path.write_text(path.read_text(encoding="utf-8").replace("sh:maxInclusive 60", 'sh:maxInclusive "bogus"^^xsd:integer'), encoding="utf-8")
    current = claim(EvidenceWorkspace.open(root))
    assert current["rules"][0]["status"] == "not_checked"
    assert current["eligibility"] == "blocked"


@pytest.mark.parametrize("output", [".evidence-review/state.sqlite3-journal", ".evidence-review/state.sqlite3-wal", ".evidence-review/state.sqlite3-shm"])
def test_cli_cannot_export_into_review_state(root, output):
    result = subprocess.run([sys.executable, "-B", "-m", "evidence_wiki", "inspect", str(root), "--json", output],
                            cwd=EXTENSION, capture_output=True, text=True, encoding="utf-8")
    assert result.returncode == 2
    assert json.loads(result.stderr)["error"] == "invalid_output"


def test_factlog_import_never_transfers_acceptance(root):
    path = root / "candidates.csv"
    fields = ["subject", "relation", "object", "source", "status", "confidence", "note"]
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fields)
        writer.writeheader()
        writer.writerow(dict(zip(fields, ["SyntheticProject", "retention", "30", "sources/retention.md#policy", "accepted", "0.9", "old approval"])))
    before = path.read_bytes()
    drafts = import_factlog(root, "candidates.csv")
    assert path.read_bytes() == before
    assert drafts["claims"][0]["external_record"]["status"] == "accepted"
    (root / "workspace.json").write_text(json.dumps(drafts), encoding="utf-8")
    current = claim(EvidenceWorkspace.open(root), "factlog-0001")
    assert current["review_state"] == "unreviewed"
    assert current["eligibility"] == "blocked"
    assert current["decisions"] == []
    assert {"evidence_unbound", "rules_unbound"}.issubset(current["reason_codes"])


def test_cli_inspection_and_stale_review_error(root):
    command = [sys.executable, "-B", "-m", "evidence_wiki"]
    inspected = subprocess.run(command + ["inspect", str(root), "--json", "snapshot.json"], cwd=EXTENSION, capture_output=True, text=True, encoding="utf-8")
    assert inspected.returncode == 0, inspected.stderr
    report = json.loads(inspected.stdout)
    assert json.loads((root / "snapshot.json").read_text(encoding="utf-8")) == report
    stale = subprocess.run(command + ["review", str(root), "retention", "accept", "--basis", "invalid", "--actor", "CLI reviewer"], cwd=EXTENSION, capture_output=True, text=True, encoding="utf-8")
    assert stale.returncode == 2
    assert json.loads(stale.stderr)["error"] == "stale_basis"
    overwrite = subprocess.run(command + ["inspect", str(root), "--json", "snapshot.json"], cwd=EXTENSION, capture_output=True, text=True, encoding="utf-8")
    assert overwrite.returncode == 2
    assert json.loads(overwrite.stderr)["error"] == "output_exists"


def test_demo_stages_and_nonempty_output_protection(tmp_path):
    destination = tmp_path / "demo"
    bundle = run_demo(destination, render=False)
    assert [sum(c["eligibility"] == "eligible" for c in s["inspection"]["claims"]) for s in bundle["stages"]] == [2, 1, 1, 2]
    assert bundle["stages"][2]["inspection"]["claims"][0]["rules"][0]["status"] == "violates"
    assert len(bundle["stages"][-1]["inspection"]["claims"][0]["decisions"]) == 2
    stored = (destination / "demo.json").read_bytes()
    with pytest.raises(EvidenceError) as raised:
        run_demo(destination, render=False)
    assert raised.value.code == "output_not_empty"
    assert (destination / "demo.json").read_bytes() == stored
