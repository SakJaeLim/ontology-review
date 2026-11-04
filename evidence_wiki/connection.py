from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path
import re
import secrets
import threading

import yaml

from .inputs import EvidenceError, canonical_json, load_manifest, read_local, safe_path, workspace_root
from .workspace import EvidenceWorkspace


PROTOCOL = "evidence-connection-v1"
MAX_SOURCE_BYTES = 1_048_576
MAX_DESCRIPTION = 4096
DESCRIPTION_PREDICATE = "urn:evidence:proposedDefinition"
RULE = '''@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
<urn:evidence:DefinitionShape> a sh:NodeShape ;
  sh:targetSubjectsOf <urn:evidence:proposedDefinition> ;
  sh:property [ sh:path <urn:evidence:proposedDefinition> ;
    sh:datatype xsd:string ; sh:minCount 1 ; sh:maxCount 1 ;
    sh:minLength 1 ; sh:maxLength 4096 ] .
'''
TYPE_MAP = {
    "CHAR": "string", "VARCHAR": "string", "NVARCHAR": "string", "NCHAR": "string",
    "TEXT": "string", "STRING": "string", "UUID": "string", "UNIQUEIDENTIFIER": "string",
    "INT": "integer", "INTEGER": "integer", "BIGINT": "integer", "SMALLINT": "integer",
    "TINYINT": "integer", "INT2": "integer", "INT4": "integer", "INT8": "integer",
    "DECIMAL": "decimal", "NUMERIC": "decimal", "FLOAT": "double", "DOUBLE": "double",
    "REAL": "double", "BOOLEAN": "boolean", "BOOL": "boolean", "BIT": "boolean",
    "DATE": "date", "DATETIME": "datetime", "TIMESTAMP": "datetime", "TIMESTAMPTZ": "datetime",
}


def _fail(message: str, code: str = "invalid_dictionary"):
    raise EvidenceError(code, message)


def _string(value, field, *, empty=False, limit=MAX_DESCRIPTION):
    if not isinstance(value, str) or len(value) > limit or (not empty and not value.strip()):
        _fail(f"{field} must be a bounded {'nonempty ' if not empty else ''}string.")
    return value


def _object(value, field):
    if not isinstance(value, dict):
        _fail(f"{field} must be an object.")
    return value


def _array(value, field, limit=200):
    if not isinstance(value, list) or len(value) > limit:
        _fail(f"{field} must be an array of at most {limit} items.")
    return value


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if not isinstance(key, str) or key in result:
            _fail("Object keys must be unique strings.")
        result[key] = value
    return result


class _DictionaryLoader(yaml.SafeLoader):
    pass


def _yaml_mapping(loader, node):
    return _unique_pairs(loader.construct_pairs(node, deep=True))


_DictionaryLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _yaml_mapping)


def _bounded(value, depth=0, budget=None):
    budget = [20_000] if budget is None else budget
    budget[0] -= 1
    if depth > 32 or budget[0] < 0:
        _fail("The document exceeds its depth or item limit.")
    if isinstance(value, dict):
        for key, item in value.items():
            _string(key, "object key", limit=512)
            _bounded(item, depth + 1, budget)
    elif isinstance(value, list):
        for item in value:
            _bounded(item, depth + 1, budget)
    elif type(value) is str:
        _string(value, "text", empty=True, limit=65_536)
        value.encode("utf-8")
    elif value is None or type(value) in (int, bool):
        pass
    elif type(value) is float and math.isfinite(value):
        pass
    else:
        _fail("Only finite JSON scalar values are supported.")


def parse_dictionary(content: str) -> tuple[dict, str]:
    """Parse a bounded native model document without YAML aliases or custom tags."""
    try:
        if not isinstance(content, str) or len(content.encode("utf-8")) > MAX_SOURCE_BYTES:
            _fail("The UTF-8 dictionary must be at most 1 MiB.")
        document_text = content.removeprefix("\ufeff")
        kind = "yaml"
        if document_text.lstrip().startswith(("{", "[")):
            try:
                document = json.loads(document_text, object_pairs_hook=_unique_pairs,
                                      parse_constant=lambda item: _fail("Non-finite numbers are not supported."))
            except json.JSONDecodeError:
                pass
            else:
                kind = "json"
        if kind == "yaml":
            for token in yaml.scan(document_text):
                if isinstance(token, (yaml.tokens.AliasToken, yaml.tokens.AnchorToken, yaml.tokens.TagToken)):
                    _fail("YAML aliases, anchors and explicit tags are not supported.")
            document = yaml.load(document_text, Loader=_DictionaryLoader)
        _bounded(document)
        return _object(document, "model document"), kind
    except (ValueError, UnicodeError, RecursionError, yaml.YAMLError) as exc:
        if isinstance(exc, EvidenceError):
            raise
        raise EvidenceError("invalid_dictionary", "The dictionary is not valid bounded UTF-8 JSON or safe YAML.") from exc


def _id(item, kind, seen):
    identifier = _string(item.get("id"), f"{kind}.id", limit=200)
    if identifier in seen:
        _fail(f"Duplicate {kind} ID: {identifier}")
    seen.add(identifier)
    return identifier


def _stable(kind, *identifiers):
    return kind + "-" + hashlib.sha256(canonical_json(identifiers).encode("utf-8")).hexdigest()[:24]


def project_dictionary(document: dict) -> tuple[dict, list[dict], list[str]]:
    """Project terms and bound descriptions; preserve all other vendor data separately."""
    data = _object(document.get("data_layer"), "data_layer")
    semantic = _object(document.get("semantic_layer"), "semantic_layer")
    tables, columns, table_of_column = {}, {}, {}
    seen = {kind: set() for kind in ("database", "schema", "table", "column", "term", "attribute")}
    for database in _array(data.get("databases"), "data_layer.databases", 50):
        _object(database, "database")
        _id(database, "database", seen["database"])
        for schema in _array(database.get("schemas", []), "schemas", 100):
            _object(schema, "schema")
            _id(schema, "schema", seen["schema"])
            for table in _array(schema.get("tables", []), "tables", 200):
                _object(table, "table")
                table_id = _id(table, "table", seen["table"])
                _string(table.get("name", ""), "table.name", empty=True, limit=200)
                for key in _array(table.get("pk", []), "table.pk"):
                    _string(key, "primary key", limit=200)
                tables[table_id] = table
                for column in _array(table.get("columns", []), "columns", 200):
                    _object(column, "column")
                    column_id = _id(column, "column", seen["column"])
                    _string(column.get("name", ""), "column.name", empty=True, limit=200)
                    for flag in ("is_nullable", "is_unique"):
                        if flag in column and type(column[flag]) is not bool:
                            _fail(f"{flag} must be a boolean.")
                    columns[column_id], table_of_column[column_id] = column, table_id
    terms = _array(semantic.get("terms"), "semantic_layer.terms", 100)
    if not terms:
        _fail("The dictionary needs at least one semantic term.")
    entities, bindings, notices = [], [], []
    for term_index, term in enumerate(terms):
        _object(term, "term")
        term_id = _id(term, "term", seen["term"])
        name = _string(term.get("name"), "term.name", limit=200)
        description = _string(term.get("description", ""), "term.description", empty=True)
        represented = _array(term.get("represents", []), "term.represents")
        if not represented or len(set(map(str, represented))) != len(represented):
            _fail("Each term must represent unique existing table IDs.")
        for table_id in represented:
            if not isinstance(table_id, str) or table_id not in tables:
                _fail("term.represents must reference table IDs, not column IDs.")
        entity_id = _stable("term", term_id)
        property_bindings, properties, names, mapped_columns = [], [], set(), set()
        for attribute_index, attribute in enumerate(_array(term.get("columns_attributes", []), "columns_attributes")):
            _object(attribute, "column attribute")
            attribute_id = _id(attribute, "attribute", seen["attribute"])
            column_id = attribute.get("column_id")
            if not isinstance(column_id, str) or column_id not in columns or table_of_column[column_id] not in represented:
                _fail("Column attributes must reference a column in a represented table.")
            column = columns[column_id]
            attribute_name = _string(attribute.get("name"), "attribute.name", limit=200)
            if attribute_name in names or column_id in mapped_columns:
                _fail("An entity cannot contain duplicate property names or ambiguous column mappings.")
            names.add(attribute_name)
            mapped_columns.add(column_id)
            sql_type = _string(column.get("type"), "column.type", limit=100)
            type_match = re.fullmatch(r"([A-Z][A-Z0-9]*)(?:\(\s*(?:MAX|\d+)(?:\s*,\s*\d+)?\s*\))?", sql_type.strip().upper())
            type_name = type_match.group(1) if type_match else None
            if type_name not in TYPE_MAP:
                _fail(f"Unsupported projected SQL type: {sql_type}")
            identifier = column.get("name") in tables[table_of_column[column_id]].get("pk", [])
            if identifier and TYPE_MAP[type_name] not in ("string", "integer"):
                _fail("A projected identifier must have a string or integer type.")
            properties.append({"name": attribute_name, "type": TYPE_MAP[type_name], "isIdentifier": identifier,
                               "description": _string(attribute.get("description", ""), "attribute.description", empty=True)})
            property_bindings.append({"attributeId": attribute_id, "columnId": column_id,
                                      "propertyName": attribute_name, "propertyIndex": attribute_index,
                                      "sourcePointer": f"/semantic_layer/terms/{term_index}/columns_attributes/{attribute_index}/description"})
        entities.append({"id": entity_id, "name": name, "description": description,
                         "properties": properties, "icon": "📄", "color": "#2458b8"})
        bindings.append({"entityId": entity_id, "termId": term_id, "tableIds": represented,
                         "sourcePointer": f"/semantic_layer/terms/{term_index}/description", "properties": property_bindings})
    if len(entities) + sum(len(entity["properties"]) for entity in entities) > 200:
        _fail("The projection exceeds 200 reviewable descriptions.")
    for foreign_key in _array(data.get("foreign_keys", []), "foreign_keys"):
        _object(foreign_key, "foreign key")
        if any(not isinstance(foreign_key.get(key), str) or foreign_key[key] not in columns for key in ("source_column_id", "target_column_id")):
            _fail("A foreign key references an unknown column.")
    for join in _array(data.get("joins", []), "joins"):
        _object(join, "join")
        if any(not isinstance(join.get(key), str) or join[key] not in tables for key in ("source_table_id", "target_table_id")):
            _fail("A join references an unknown table.")
    for foreign_key in _array(semantic.get("semantic_fks", []), "semantic_fks"):
        _object(foreign_key, "semantic foreign key")
        if (not isinstance(foreign_key.get("column_id"), str) or foreign_key["column_id"] not in columns or
                not isinstance(foreign_key.get("column_attribute_id"), str) or foreign_key["column_attribute_id"] not in seen["attribute"]):
            _fail("A semantic foreign key references an unknown column or attribute.")
    for label, value in (("database columns and samples", data), ("foreign keys and joins", data.get("foreign_keys") or data.get("joins")),
                         ("semantic foreign keys", semantic.get("semantic_fks")), ("SQL attributes", semantic.get("sql_attributes")),
                         ("custom analyses", semantic.get("custom_analyses")), ("zones", document.get("zones"))):
        if value:
            notices.append(f"Original {label} remain in the raw source. Only term and attribute descriptions are projected for review.")
    notices.extend(["Relationships are not inferred because the source does not declare their cardinality.",
                    "Generated evidence extracts represent the supplied dictionary and editor submission; they are not independent factual sources.",
                    "Checks cover mapping references and nonempty description structure. Human review does not prove semantic equivalence or factual truth.",
                    "Fabric IQ naming and identifier restrictions are separate from this local review."])
    ontology = {"name": "Imported NVIDIA dictionary", "description": "Definition proposals linked to a preserved Auto Ontology model.",
                "entityTypes": entities, "relationships": []}
    return ontology, bindings, notices


def _structure(ontology):
    result = deepcopy(ontology)
    result.pop("name", None)
    result.pop("description", None)
    for entity in result.get("entityTypes", []):
        entity.pop("description", None)
        for prop in entity.get("properties", []):
            prop.pop("description", None)
    return result


class ConnectionWorkspace:
    """Single-process owner of imported sources, immutable projections and explicit reviews."""

    def __init__(self, root: Path):
        self.root = workspace_root(root)
        self.lock = threading.RLock()
        if not (self.root / "workspace.json").exists() and any(path.name != ".connection" for path in self.root.iterdir()):
            _fail("Use an empty directory or an existing connection workspace.", "unmanaged_workspace")
        self._manifest()

    def _manifest(self):
        path = safe_path(self.root, "workspace.json")
        if not path.exists():
            return None, "empty"
        if path.stat().st_nlink != 1:
            _fail("The connection manifest must not have hard links.", "unsafe_state")
        manifest = load_manifest(self.root)
        metadata = manifest.get("connection")
        if not isinstance(metadata, dict) or metadata.get("protocol") != PROTOCOL:
            _fail("This workspace belongs to a different application.", "unmanaged_workspace")
        source = read_local(self.root, "workspace.json")
        return manifest, source.digest

    def _checked_file(self, record):
        source = read_local(self.root, record["path"])
        if source.availability != "available" or source.digest != record["sha256"]:
            _fail("A preserved connection resource changed or is unavailable.", "source_integrity")
        return source.content

    def _state(self):
        manifest, revision = self._manifest()
        if manifest is None:
            return {"revision": revision, "ontology": None, "source": None, "bindings": [], "notices": [], "inspection": None}
        connection = manifest["connection"]
        self._checked_file(connection["source"])
        ontology = json.loads(self._checked_file(connection["projection"]))
        return {"revision": revision, "ontology": ontology, "source": connection["source"],
                "bindings": connection["bindings"], "notices": connection["notices"],
                "inspection": EvidenceWorkspace.open(self.root).inspect()}

    def state(self):
        with self.lock:
            return self._state()

    def _expected(self, expected):
        current = self._state()
        if not isinstance(expected, str) or expected != current["revision"]:
            _fail("The workspace changed. Reload it before saving or reviewing.", "stale_revision")
        return current

    def _immutable(self, relative, content):
        path = safe_path(self.root, relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        path = safe_path(self.root, relative)
        if path.exists():
            if path.stat().st_nlink != 1 or path.read_bytes() != content:
                _fail("An immutable connection resource conflicts with existing content.", "source_integrity")
        else:
            with path.open("xb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
        return {"path": relative, "sha256": hashlib.sha256(content).hexdigest()}

    def _publish(self, source, original, ontology, bindings, notices):
        generation = secrets.token_hex(16)
        prefix = f".connection/generations/{generation}"
        projection = self._immutable(prefix + "/ontology.json", canonical_json(ontology).encode("utf-8"))
        rule_path = prefix + "/description.ttl"
        self._immutable(rule_path, RULE.encode("utf-8"))
        claims = []
        original_ontology, _, _ = project_dictionary(original)
        for entity_index, (entity, binding) in enumerate(zip(ontology["entityTypes"], bindings, strict=True)):
            source_entity = original_ontology["entityTypes"][entity_index]
            descriptions = [(entity["id"], entity["name"], entity["description"], source_entity["description"], binding["sourcePointer"], f"/entityTypes/{entity_index}/description")]
            for property_index, (prop, prop_binding) in enumerate(zip(entity["properties"], binding["properties"], strict=True)):
                descriptions.append((_stable("attribute", binding["termId"], prop_binding["attributeId"]),
                                     entity["name"] + ": " + prop["name"], prop["description"], source_entity["properties"][property_index]["description"],
                                     prop_binding["sourcePointer"], f"/entityTypes/{entity_index}/properties/{property_index}/description"))
            for identifier, title, proposed, prior, source_pointer, editor_pointer in descriptions:
                lines = ["NVIDIA pointer: " + source_pointer, "Original SHA-256: " + source["sha256"],
                         "Original description: " + json.dumps(prior, ensure_ascii=False), "Editor pointer: " + editor_pointer,
                         "Proposed description: " + json.dumps(proposed, ensure_ascii=False)]
                extract_path = prefix + "/" + identifier + ".txt"
                self._immutable(extract_path, ("\n".join(lines) + "\n").encode("utf-8"))
                claims.append({"id": identifier, "title": title, "subject": "urn:evidence:" + identifier,
                               "predicate": DESCRIPTION_PREDICATE, "value": proposed, "datatype": "http://www.w3.org/2001/XMLSchema#string",
                               "evidence": [{"path": extract_path, "start_line": line, "end_line": line, "text": lines[line - 1]} for line in (3, 5)],
                               "rules": [rule_path], "wiki_pages": ["wiki/" + entity["id"] + ".md"]})
        manifest = {"schema_version": 1, "name": ontology["name"], "claims": claims,
                    "connection": {"protocol": PROTOCOL, "source": source, "projection": projection,
                                   "bindings": bindings, "notices": notices, "generation": generation}}
        encoded = canonical_json(manifest).encode("utf-8")
        if len(encoded) > MAX_SOURCE_BYTES:
            _fail("Generated review manifest exceeds 1 MiB.")
        candidate = safe_path(self.root, prefix + "/workspace.json")
        self._immutable(prefix + "/workspace.json", encoded)
        load_manifest(candidate.parent)
        destination = safe_path(self.root, "workspace.json")
        if destination.exists() and destination.stat().st_nlink != 1:
            _fail("The connection manifest must not have hard links.", "unsafe_state")
        pending = safe_path(self.root, prefix + "/publish.json")
        self._immutable(prefix + "/publish.json", encoded)
        os.replace(pending, destination)
        return self._state()

    def import_dictionary(self, *, expectedRevision, filename, content):
        with self.lock:
            current = self._expected(expectedRevision)
            filename = _string(filename, "filename", limit=200)
            original, kind = parse_dictionary(content)
            ontology, bindings, notices = project_dictionary(original)
            raw = content.encode("utf-8")
            digest = hashlib.sha256(raw).hexdigest()
            if current["source"] and current["source"]["sha256"] == digest:
                return current
            source = self._immutable(f".connection/sources/{digest}.txt", raw)
            source.update({"filename": filename, "format": kind, "vendor": "NVIDIA Auto Ontology"})
            return self._publish(source, original, ontology, bindings, notices)

    def save_editor(self, *, expectedRevision, ontology):
        with self.lock:
            current = self._expected(expectedRevision)
            if current["ontology"] is None:
                _fail("Import a dictionary before opening the editor.", "no_dictionary")
            _bounded(ontology)
            _object(ontology, "ontology")
            _string(ontology.get("name"), "ontology.name", limit=200)
            _string(ontology.get("description"), "ontology.description", empty=True)
            try:
                if canonical_json(_structure(ontology)) != canonical_json(_structure(current["ontology"])):
                    _fail("Only ontology title/description and bound entity/property descriptions can be changed. Keep identities, order, names, types and relationships unchanged.", "unsupported_edit")
                for entity in ontology["entityTypes"]:
                    _string(entity.get("description"), "entity.description", empty=True)
                    for prop in entity["properties"]:
                        _string(prop.get("description"), "property.description", empty=True)
            except (AttributeError, KeyError, TypeError) as exc:
                raise EvidenceError("unsupported_edit", "The editor document does not preserve its bound structure.") from exc
            if ontology == current["ontology"]:
                return current
            original, _ = parse_dictionary(self._checked_file(current["source"]).decode("utf-8"))
            return self._publish(current["source"], original, ontology, current["bindings"], current["notices"])

    def review(self, *, expectedRevision, claimId, basis, action, actor):
        with self.lock:
            self._expected(expectedRevision)
            EvidenceWorkspace.open(self.root).review(claimId, action, basis=basis, actor=actor)
            return self._state()

    def export(self):
        with self.lock:
            state = self._state()
            if state["source"] is None:
                _fail("Import a dictionary before exporting.", "no_dictionary")
            return {"protocol": PROTOCOL, "revision": state["revision"], "source": {**state["source"],
                    "content": self._checked_file(state["source"]).decode("utf-8")},
                    "ontology": state["ontology"], "bindings": state["bindings"], "notices": state["notices"]}
