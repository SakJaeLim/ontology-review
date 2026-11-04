from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from importlib.resources import files
import json
import os
import threading

import pytest
import yaml

from evidence_wiki.connection import ConnectionWorkspace, parse_dictionary, project_dictionary
from evidence_wiki.inputs import EvidenceError


@pytest.fixture
def original():
    return files("evidence_wiki").joinpath("web/example.json").read_text(encoding="utf-8")


@pytest.fixture
def connection(tmp_path):
    return ConnectionWorkspace(tmp_path)


def imported(connection, original):
    return connection.import_dictionary(expectedRevision="empty", filename="example.json", content=original)


def test_raw_bytes_unicode_bom_and_newlines_are_preserved(connection, original):
    raw = "\ufeff" + original.replace("\n", "\r\n")
    state = imported(connection, raw)
    assert (connection.root / state["source"]["path"]).read_bytes() == raw.encode("utf-8")
    assert connection.export()["source"]["content"] == raw
    assert state["source"]["format"] == "json"
    assert len(state["inspection"]["claims"]) == 5
    assert all(claim["eligibility"] == "unreviewed" for claim in state["inspection"]["claims"])
    assert state["bindings"][0]["tableIds"] == ["table-dataset"]
    assert state["bindings"][0]["properties"][0]["columnId"] == "column-dataset-id"


@pytest.mark.parametrize("flow_style", [False, True])
def test_safe_yaml_has_the_same_projection(connection, original, flow_style):
    document = json.loads(original)
    raw = yaml.safe_dump(document, allow_unicode=True, sort_keys=False, default_flow_style=flow_style)
    state = imported(connection, raw)
    expected, _, _ = project_dictionary(document)
    assert state["ontology"] == expected
    assert state["source"]["format"] == "yaml"
    assert connection.export()["source"]["content"] == raw


@pytest.mark.parametrize("raw", ['{"x":1,"x":2}', "x: 1\nx: 2", "{x: 1, x: 2}",
    "x: &source [1]\ny: *source", "{x: &source [1], y: *source}",
    "x: !!str 12", "{x: !!str 12}", "x: .nan", "{x: .nan}", "x: 2000-01-01",
    '{"x": NaN}', '{"x": Infinity}', '{"x": -Infinity}', "[]", "[" * 40 + "0" + "]" * 40])
def test_unsafe_or_ambiguous_inputs_are_rejected(raw):
    with pytest.raises(EvidenceError):
        parse_dictionary(raw)


@pytest.mark.parametrize("mutation", [
    lambda data: data["semantic_layer"]["terms"][0].update(represents=["column-dataset-id"]),
    lambda data: data["semantic_layer"]["terms"][0]["columns_attributes"][0].update(column_id="missing"),
    lambda data: data["semantic_layer"]["terms"][0]["columns_attributes"][0].update(column_id="column-org-id"),
    lambda data: data["semantic_layer"]["terms"].append(deepcopy(data["semantic_layer"]["terms"][0])),
    lambda data: data["data_layer"]["databases"][0]["schemas"][0]["tables"][0]["columns"][0].update(type="BLOB"),
    lambda data: data["data_layer"]["databases"][0]["schemas"][0]["tables"][0]["columns"][0].update(type="INTEGER ARRAY"),
    lambda data: data["data_layer"].update(foreign_keys=[{"source_column_id": [], "target_column_id": "missing"}]),
])
def test_bad_mappings_do_not_publish(connection, original, mutation):
    state = imported(connection, original)
    before = (connection.root / "workspace.json").read_bytes()
    malformed = json.loads(original)
    mutation(malformed)
    with pytest.raises(EvidenceError):
        connection.import_dictionary(expectedRevision=state["revision"], filename="bad.json", content=json.dumps(malformed))
    assert (connection.root / "workspace.json").read_bytes() == before


def test_explicit_review_edit_noop_and_source_refresh(connection, original):
    state = imported(connection, original)
    first = state["inspection"]["claims"][0]
    reviewed = connection.review(expectedRevision=state["revision"], claimId=first["id"], basis=first["basis"], action="accept", actor="Synthetic reviewer")
    assert reviewed["inspection"]["claims"][0]["eligibility"] == "eligible"
    draft = deepcopy(state["ontology"])
    draft["entityTypes"][0]["description"] = "사용자가 편집기에서 수정한 합성 정의입니다."
    edited = connection.save_editor(expectedRevision=state["revision"], ontology=draft)
    current = edited["inspection"]["claims"][0]
    assert current["id"] == first["id"] and current["value"] == draft["entityTypes"][0]["description"]
    assert current["eligibility"] == "blocked" and current["review_state"] == "needs_review"
    assert len(current["decisions"]) == 1 and current["basis"] != first["basis"]
    assert connection.save_editor(expectedRevision=edited["revision"], ontology=draft)["revision"] == edited["revision"]
    assert connection.import_dictionary(expectedRevision=edited["revision"], filename="same.json", content=original)["ontology"] == draft
    with pytest.raises(EvidenceError, match="changed"):
        connection.save_editor(expectedRevision=state["revision"], ontology=state["ontology"])
    with pytest.raises(EvidenceError) as error:
        connection.review(expectedRevision=edited["revision"], claimId=first["id"], basis=first["basis"], action="accept", actor="Synthetic reviewer")
    assert error.value.code == "stale_basis"
    connection.review(expectedRevision=edited["revision"], claimId=first["id"], basis=current["basis"], action="accept", actor="Synthetic reviewer")
    changed = json.loads(original)
    changed["semantic_layer"]["terms"][0]["description"] = "원본 데이터 사전의 새로운 합성 정의입니다."
    refreshed = connection.import_dictionary(expectedRevision=edited["revision"], filename="changed.json", content=json.dumps(changed, ensure_ascii=False))
    assert refreshed["inspection"]["claims"][0]["eligibility"] == "blocked"
    assert len(refreshed["inspection"]["claims"][0]["decisions"]) == 2
    assert (connection.root / state["source"]["path"]).read_text(encoding="utf-8") == original


@pytest.mark.parametrize("mutation", [
    lambda ontology: ontology["entityTypes"][0].update(name="DifferentName"),
    lambda ontology: ontology["entityTypes"].reverse(),
    lambda ontology: ontology["entityTypes"][0]["properties"].reverse(),
    lambda ontology: ontology.update(relationships=[{"id": "new"}]),
    lambda ontology: ontology["entityTypes"][0]["properties"][0].update(type="boolean"),
    lambda ontology: ontology["entityTypes"][0]["properties"][0].update(isIdentifier=1),
])
def test_unsupported_editor_structure_preserves_current_manifest(connection, original, mutation):
    state = imported(connection, original)
    draft = deepcopy(state["ontology"])
    mutation(draft)
    with pytest.raises(EvidenceError) as error:
        connection.save_editor(expectedRevision=state["revision"], ontology=draft)
    assert error.value.code == "unsupported_edit"
    assert connection.state()["revision"] == state["revision"]


def test_empty_description_can_be_edited_but_cannot_be_approved(connection, original):
    state = imported(connection, original)
    draft = deepcopy(state["ontology"])
    draft["entityTypes"][0]["description"] = ""
    changed = connection.save_editor(expectedRevision=state["revision"], ontology=draft)
    claim = changed["inspection"]["claims"][0]
    assert claim["rules"][0]["status"] == "violates"
    with pytest.raises(EvidenceError) as error:
        connection.review(expectedRevision=changed["revision"], claimId=claim["id"], basis=claim["basis"], action="accept", actor="Synthetic reviewer")
    assert error.value.code == "checks_failed"


def test_raw_source_tamper_prevents_review(connection, original):
    state = imported(connection, original)
    (connection.root / state["source"]["path"]).write_text("changed", encoding="utf-8")
    claim = state["inspection"]["claims"][0]
    with pytest.raises(EvidenceError) as error:
        connection.review(expectedRevision=state["revision"], claimId=claim["id"], basis=claim["basis"], action="accept", actor="Synthetic reviewer")
    assert error.value.code == "source_integrity"


def test_unmanaged_workspace_is_not_modified(tmp_path):
    (tmp_path / "private.txt").write_text("keep", encoding="utf-8")
    with pytest.raises(EvidenceError) as error:
        ConnectionWorkspace(tmp_path)
    assert error.value.code == "unmanaged_workspace"
    assert (tmp_path / "private.txt").read_text() == "keep"


def test_manifest_hardlink_is_not_written(connection, original, tmp_path):
    state = imported(connection, original)
    target = tmp_path / "manifest-alias"
    try:
        os.link(tmp_path / "workspace.json", target)
    except OSError:
        pytest.skip("The platform denied hardlink creation.")
    before = target.read_bytes()
    with pytest.raises(EvidenceError) as error:
        connection.save_editor(expectedRevision=state["revision"], ontology=state["ontology"])
    assert error.value.code == "unsafe_state"
    assert target.read_bytes() == before


def test_primary_keys_use_column_names_not_column_ids(original):
    document = json.loads(original)
    table = document["data_layer"]["databases"][0]["schemas"][0]["tables"][0]
    table["columns"][1]["name"] = table["columns"][0]["id"]
    table["pk"] = [table["columns"][0]["id"]]
    ontology, _, _ = project_dictionary(document)
    assert ontology["entityTypes"][0]["properties"][0]["isIdentifier"] is False
    assert ontology["entityTypes"][0]["properties"][1]["isIdentifier"] is True


@pytest.mark.parametrize("failure", ["generation", "replace"])
def test_interrupted_publication_keeps_previous_manifest_and_decisions(connection, original, monkeypatch, failure):
    state = imported(connection, original)
    claim = state["inspection"]["claims"][0]
    connection.review(expectedRevision=state["revision"], claimId=claim["id"], basis=claim["basis"], action="accept", actor="Synthetic reviewer")
    before = (connection.root / "workspace.json").read_bytes()
    draft = deepcopy(state["ontology"])
    draft["entityTypes"][0]["description"] = "Interrupted edit"
    write = connection._immutable

    def fail_write(relative, content):
        if relative.endswith("/description.ttl"):
            raise OSError("Synthetic disk failure")
        return write(relative, content)

    def fail_replace(*args):
        raise OSError("Synthetic publication failure")

    with monkeypatch.context() as change:
        if failure == "generation":
            change.setattr(connection, "_immutable", fail_write)
        else:
            change.setattr("evidence_wiki.connection.os.replace", fail_replace)
        with pytest.raises(OSError):
            connection.save_editor(expectedRevision=state["revision"], ontology=draft)
    assert (connection.root / "workspace.json").read_bytes() == before
    current = connection.state()
    assert current["revision"] == state["revision"] and current["ontology"] == state["ontology"]
    assert current["inspection"]["claims"][0]["eligibility"] == "eligible"
    assert len(current["inspection"]["claims"][0]["decisions"]) == 1


def test_concurrent_editor_saves_have_only_one_winner(connection, original):
    state = imported(connection, original)
    gate = threading.Barrier(2)

    def edit(description):
        draft = deepcopy(state["ontology"])
        draft["entityTypes"][0]["description"] = description
        gate.wait(timeout=5)
        try:
            return connection.save_editor(expectedRevision=state["revision"], ontology=draft)
        except EvidenceError as exc:
            return exc.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(edit, ["First concurrent draft", "Second concurrent draft"]))
    assert results.count("stale_revision") == 1
    winner = next(result for result in results if isinstance(result, dict))
    assert connection.state()["ontology"] == winner["ontology"]


def test_observed_editor_revert_does_not_restore_approval(connection, original):
    state = imported(connection, original)
    claim = state["inspection"]["claims"][0]
    connection.review(expectedRevision=state["revision"], claimId=claim["id"], basis=claim["basis"], action="accept", actor="Synthetic reviewer")
    changed = deepcopy(state["ontology"])
    changed["entityTypes"][0]["description"] = "Temporary observed edit"
    edited = connection.save_editor(expectedRevision=state["revision"], ontology=changed)
    reverted = connection.save_editor(expectedRevision=edited["revision"], ontology=state["ontology"])
    current = reverted["inspection"]["claims"][0]
    assert current["value"] == claim["value"] and current["basis"] != claim["basis"]
    assert current["review_state"] == "needs_review" and len(current["decisions"]) == 1
