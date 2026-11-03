from __future__ import annotations

import re

from rdflib import BNode, Graph, Literal, RDF, URIRef
from rdflib.namespace import SH, XSD
from pyshacl import validate

from .inputs import DATATYPES


POLICY_REVISION = "evidence-review-1:claim-scoped-local-shacl-property-bounds-v2"
SUPPORTED_CONSTRAINTS = {SH.datatype, SH.minCount, SH.maxCount, SH.minInclusive, SH.maxInclusive,
                         SH.minLength, SH.maxLength}
METADATA = {SH.name, SH.description, SH.message}
SUPPORTED_PREDICATES = SUPPORTED_CONSTRAINTS | METADATA | {
    RDF.type, SH.targetNode, SH.targetSubjectsOf, SH.property, SH.path,
}


def valid_claim_value(claim: dict) -> bool:
    value = claim["value"]
    lexical = ("true" if value else "false") if type(value) is bool else str(value)
    patterns = {
        str(XSD.integer): r"[+-]?[0-9]+",
        str(XSD.decimal): r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)",
        str(XSD.boolean): r"true|false|0|1",
    }
    pattern = patterns.get(claim["datatype"])
    return pattern is None or re.fullmatch(pattern, lexical) is not None


def check_rule(content: bytes, claim: dict) -> dict:
    result = {"status": "not_checked", "focus_count": 0, "messages": []}
    try:
        graph = Graph().parse(data=content.decode("utf-8"), format="turtle")
        if not 0 < len(graph) <= 1000:
            raise ValueError("Rule graph must contain 1 to 1000 triples.")
        for subject, predicate, obj in graph:
            if predicate not in SUPPORTED_PREDICATES:
                raise ValueError(f"Unsupported rule predicate: {predicate}")
            if predicate == RDF.type and obj not in (SH.NodeShape, SH.PropertyShape):
                raise ValueError("Only sh:NodeShape and sh:PropertyShape types are supported.")
            if predicate in METADATA and not isinstance(obj, Literal):
                raise ValueError("Rule descriptions must be literals.")
        shapes = set(graph.subjects(RDF.type, SH.NodeShape))
        if not shapes:
            raise ValueError("A typed sh:NodeShape is required.")
        owned_nodes = set(shapes)
        targets = set()
        applicable_properties = []
        triple_subject = URIRef(claim["subject"])
        triple_predicate = URIRef(claim["predicate"])
        for shape in shapes:
            if not isinstance(shape, (URIRef, BNode)):
                raise ValueError("Invalid node shape.")
            if set(graph.predicates(shape)) - ({RDF.type, SH.targetNode, SH.targetSubjectsOf, SH.property} | METADATA):
                raise ValueError("Only property constraints are supported on node shapes.")
            shape_targets = list(graph.objects(shape, SH.targetNode))
            predicate_targets = list(graph.objects(shape, SH.targetSubjectsOf))
            if not shape_targets and not predicate_targets:
                raise ValueError("Every node shape requires an explicit supported target.")
            if any(not isinstance(target, URIRef) for target in shape_targets + predicate_targets):
                raise ValueError("Rule targets must be IRIs.")
            matches_subject = triple_subject in shape_targets or triple_predicate in predicate_targets
            properties = list(graph.objects(shape, SH.property))
            if not properties:
                raise ValueError("Every node shape requires a property constraint.")
            for prop in properties:
                owned_nodes.add(prop)
                if not isinstance(prop, (URIRef, BNode)):
                    raise ValueError("Property shapes must be nodes.")
                predicates = set(graph.predicates(prop))
                if predicates - (SUPPORTED_CONSTRAINTS | METADATA | {RDF.type, SH.path}):
                    raise ValueError("Unsupported property shape structure.")
                paths = list(graph.objects(prop, SH.path))
                if len(paths) != 1 or not isinstance(paths[0], URIRef):
                    raise ValueError("Property paths must be one direct IRI.")
                if not predicates & SUPPORTED_CONSTRAINTS:
                    raise ValueError("An actual property constraint is required.")
                if matches_subject and paths[0] == triple_predicate:
                    targets.add(triple_subject)
                    applicable_properties.append((shape, prop))
                for predicate in SUPPORTED_CONSTRAINTS:
                    values = list(graph.objects(prop, predicate))
                    if len(values) > 1:
                        raise ValueError("Constraint predicates may occur once per property shape.")
                    for value in values:
                        if predicate == SH.datatype:
                            if str(value) not in DATATYPES or not isinstance(value, URIRef):
                                raise ValueError("Unsupported datatype constraint.")
                        elif predicate in {SH.minCount, SH.maxCount, SH.minLength, SH.maxLength}:
                            if not isinstance(value, Literal) or value.datatype != XSD.integer or type(value.toPython()) is not int or not 0 <= value.toPython() <= 100_000:
                                raise ValueError("Count and length constraints require bounded nonnegative integers.")
                        elif (not isinstance(value, Literal) or value.datatype not in (XSD.integer, XSD.decimal) or
                              value.ill_typed is True or
                              not re.fullmatch(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)", str(value))):
                            raise ValueError("Inclusive bounds must be valid finite numeric literals.")
        if set(graph.subjects()) - owned_nodes:
            raise ValueError("Unattached rule nodes are unsupported.")
        result["focus_count"] = len(targets)
        if not targets:
            result["messages"] = ["No rule target matches this claim. Validation was not counted as a pass."]
            return result
        scoped_rules = Graph()
        for shape, prop in applicable_properties:
            scoped_rules.add((shape, RDF.type, SH.NodeShape))
            scoped_rules.add((shape, SH.targetNode, triple_subject))
            scoped_rules.add((shape, SH.property, prop))
            for predicate in METADATA:
                for value in graph.objects(shape, predicate):
                    scoped_rules.add((shape, predicate, value))
            for triple in graph.triples((prop, None, None)):
                scoped_rules.add(triple)
        data = Graph()
        data.add((triple_subject, triple_predicate, Literal(claim["value"], datatype=URIRef(claim["datatype"]), normalize=False)))
        conforms, report, _ = validate(
            data_graph=data, shacl_graph=scoped_rules, inference="none", advanced=False,
            js=False, do_owl_imports=False, inplace=False, abort_on_first=False,
            allow_infos=False, allow_warnings=False, meta_shacl=False,
        )
        if not isinstance(report, Graph):
            raise ValueError("SHACL did not return a validation report.")
        result["status"] = "conforms" if conforms else "violates"
        result["messages"] = sorted({str(message)[:2000] for message in report.objects(None, SH.resultMessage)})[:30]
        return result
    except Exception as exc:
        result["status"] = "not_checked"
        result["messages"] = [f"Rule not checked: {type(exc).__name__}: {str(exc)[:1000]}"]
        return result
