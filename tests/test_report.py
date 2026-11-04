import json
import re
from html.parser import HTMLParser

import pytest

from evidence_wiki.report import render_report


def embedded_report(document):
    data = re.search(r'<script id="report-data" type="application/json">(.*?)</script>',
                     document, re.DOTALL)
    assert data is not None
    return json.loads(data.group(1))


def test_preserves_single_inspection_and_review_history(tmp_path):
    report = {"schema_version": 1, "workspace_name": "Sample", "claims": [{
        "id": "retention", "review_state": "needs_review", "eligibility": "blocked",
        "decisions": [{"action": "approve", "actor": "synthetic-reviewer", "basis": "old-basis"}],
        "evidence": [{"path": "source.md", "start_line": 2, "end_line": 3,
                      "expected_text": "30 days", "actual_text": "90 days"}]}]}
    output = tmp_path / "nested" / "report.html"
    render_report(report, output)
    document = output.read_text(encoding="utf-8")
    assert embedded_report(document) == report
    assert 'lang="ko"' in document
    assert "근거 검토" in document
    assert "Evidence review" in document
    assert "Current reuse eligibility" in document
    assert "Decision history" in document
    assert "does not block native LLM Wiki approvals or answers" in document


def test_escapes_html_script_boundaries_and_unicode_separators(tmp_path):
    attack = '</script><script>alert("injected")</script>&<img src=x onerror=alert(1)>\u2028\u2029'
    report = {"workspace_name": attack, "claims": [{"id": attack, "title": attack}]}
    output = tmp_path / "report.html"
    render_report(report, output)
    document = output.read_text(encoding="utf-8")
    assert embedded_report(document) == report
    assert attack not in document
    assert '\\u003c/script\\u003e' in document
    assert '\\u2028\\u2029' in document
    assert "\u2028" not in document and "\u2029" not in document
    assert "innerHTML" not in document and "document.write" not in document
    assert ".textContent" in document


def test_demo_keeps_recorded_stages_and_labels_them_as_snapshots(tmp_path):
    stages = [{"id": label, "label_ko": label, "label_en": label,
               "inspection": {"observed_at": f"2026-11-03T12:00:0{index}Z",
                              "claims": [{"id": "retention", "value": index}]}}
              for index, label in enumerate(["approved", "source-changed", "rule-failed", "reviewed"])]
    report = {"schema_version": 1, "demo": True, "stages": stages}
    output = tmp_path / "report.html"
    render_report(report, output, language="en")
    document = output.read_text(encoding="utf-8")
    assert embedded_report(document) == report
    assert 'lang="en"' in document
    assert "실행 기록" in document and "Execution records" in document
    assert "Synthetic demo" in document
    assert "does not monitor file changes in real time" in document


@pytest.mark.parametrize("value", [2**53, 2**53 + 1, -(2**53 + 1), 2**100])
def test_html_preserves_unsafe_integer_lexemes_without_mutating_the_inspection(tmp_path, value):
    report = {"claims": [{"id": "large", "value": value, "datatype": "http://www.w3.org/2001/XMLSchema#integer"}]}
    bundle = {"demo": True, "stages": [{"id": "large", "inspection": report}]}
    output = tmp_path / "report.html"
    for original in (report, bundle):
        render_report(original, output)
        encoded = embedded_report(output.read_text(encoding="utf-8"))
        inspection = encoded["stages"][0]["inspection"] if "stages" in encoded else encoded
        assert inspection["claims"][0]["value"] == str(value)
        assert inspection["claims"][0]["datatype"] == report["claims"][0]["datatype"]
        assert report["claims"][0]["value"] == value
        assert type(report["claims"][0]["value"]) is int


@pytest.mark.parametrize("value", [2**53 - 1, -(2**53 - 1), True, False, 1.25, "9007199254740993"])
def test_html_retains_safe_scalar_types(tmp_path, value):
    report = {"claims": [{"id": "value", "value": value}]}
    output = tmp_path / "report.html"
    render_report(report, output)
    actual = embedded_report(output.read_text(encoding="utf-8"))["claims"][0]["value"]
    assert actual == value
    assert type(actual) is type(value)


class ResourceParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.resources = []

    def handle_starttag(self, tag, attributes):
        self.resources.extend(value for name, value in attributes if name in {"src", "href", "srcset"})


def test_report_has_no_external_or_file_resources(tmp_path):
    output = tmp_path / "report.html"
    render_report({"claims": []}, output)
    document = output.read_text(encoding="utf-8")
    parser = ResourceParser()
    parser.feed(document)
    assert parser.resources == []
    assert "fetch(" not in document and "XMLHttpRequest" not in document
    assert "@import" not in document and "url(" not in document
    assert "default-src 'none'" in document


def test_export_retains_vendored_design_licenses_and_decorative_icons(tmp_path):
    output = tmp_path / "report.html"
    render_report({"claims": []}, output)
    document = output.read_text(encoding="utf-8")
    assert "Copyright (c) 2021 Adam Argyle" in document
    assert "Copyright (c) 2026 Lucide Icons and Contributors" in document
    assert "Copyright (c) 2013-present Cole Bemis" in document
    assert "THE SOFTWARE IS PROVIDED" in document
    assert 'aria-hidden="true"><svg' in document
    assert "__DESIGN_TOKENS__" not in document and "__SEARCH_ICON__" not in document


@pytest.mark.parametrize("language", ["de", "<script>", ""])
def test_rejects_unsupported_language_without_creating_file(tmp_path, language):
    output = tmp_path / "report.html"
    with pytest.raises(ValueError, match="language"):
        render_report({}, output, language=language)
    assert not output.exists()
