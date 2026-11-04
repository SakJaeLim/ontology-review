from copy import deepcopy
from contextlib import contextmanager, nullcontext
import http.client
from importlib.resources import files
import json
import threading

import pytest

from evidence_wiki.connection import ConnectionWorkspace, PROTOCOL
from evidence_wiki.server import ConnectionServer, MAX_BODY_BYTES


@pytest.fixture
def server(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    editor = tmp_path / "editor"
    editor.mkdir()
    (editor / "index.html").write_text("<title>Actual editor build fixture</title>", encoding="utf-8")
    with ConnectionServer(ConnectionWorkspace(workspace), editor, 0) as running:
        thread = threading.Thread(target=running.serve_forever, daemon=True)
        thread.start()
        yield running
        running.shutdown()
        thread.join(timeout=3)


def request(server, path, body=None, *, extra=None, session=True):
    headers = {"Host": server.host}
    if session:
        headers["Cookie"] = "evidence_connection=" + server.session
    if body is not None:
        headers.update({"Content-Type": "application/json", "Origin": server.origin, "X-CSRF-Token": server.csrf})
    headers.update(extra or {})
    connection = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=10)
    try:
        connection.request("POST" if body is not None else "GET", path, body=None if body is None else json.dumps(body).encode(), headers=headers)
        response = connection.getresponse()
        data = response.read()
        return response.status, dict(response.getheaders()), data
    finally:
        connection.close()


@contextmanager
def early_rejection(server):
    """An unread rejected POST may be reset; the next authenticated read must succeed."""
    before = server.workspace.state()
    try:
        yield
    except (ConnectionResetError, ConnectionAbortedError):
        pass
    status, _, raw = request(server, "/api/state")
    assert status == 200 and json.loads(raw) == before


def test_session_is_stable_and_api_requires_cookie(server):
    status, headers, data = request(server, "/api/session", session=False)
    first = json.loads(data)
    assert status == 200 and first["protocol"] == PROTOCOL
    assert "HttpOnly" in headers["Set-Cookie"] and "SameSite=Strict" in headers["Set-Cookie"]
    assert json.loads(request(server, "/api/session")[2])["csrfToken"] == first["csrfToken"]
    assert request(server, "/api/state", session=False)[0] == 403
    assert "Access-Control-Allow-Origin" not in headers


@pytest.mark.parametrize("extra", [
    {"Host": "attacker.test"}, {"Origin": "https://attacker.test"},
    {"X-CSRF-Token": "wrong"}, {"Cookie": "evidence_connection=wrong"},
    {"Sec-Fetch-Site": "cross-site"}, {"Origin": "null"},
])
def test_cross_site_or_unauthenticated_mutations_are_rejected(server, extra):
    body = {"expectedRevision": "empty", "filename": "security-fixture.json",
            "content": files("evidence_wiki").joinpath("web/example.json").read_text(encoding="utf-8")}
    with early_rejection(server):
        assert request(server, "/api/import", body, extra=extra)[0] == 403
    assert server.workspace.state()["revision"] == "empty"


def test_body_and_static_path_boundaries(server):
    with early_rejection(server):
        assert request(server, "/api/editor", {}, extra={"Content-Type": "text/plain"})[0] == 415
    with early_rejection(server):
        assert request(server, "/api/editor", {}, extra={"Content-Length": str(MAX_BODY_BYTES + 1)})[0] == 413
    assert request(server, "/api/editor", {"unexpected": "value"})[0] == 400
    assert request(server, "/editor/%2e%2e/workspace/workspace.json")[0] != 200
    assert request(server, "/editor/C:/Windows/win.ini")[0] != 200
    assert request(server, "/editor/")[0] == 200
    assert request(server, "/api/session", extra={"Origin": "https://attacker.test"}, session=False)[0] == 403


@pytest.mark.parametrize("headers, body", [
    ([("Host", "attacker.test")], b"{}"),
    ([("Origin", "http://127.0.0.1:1")], b"{}"),
    ([("X-CSRF-Token", "duplicate")], b"{}"),
    ([("Content-Length", "2")], b"{}"),
    ([("Transfer-Encoding", "chunked")], b"{}"),
    ([], b'{"expectedRevision":"empty","expectedRevision":"other","ontology":{}}'),
    ([], b'{"expectedRevision":"empty","ontology":NaN}'),
    ([], b'{"expectedRevision":"empty","ontology":"\xff"}'),
])
def test_duplicate_headers_and_malformed_bodies_cannot_write(server, headers, body):
    with early_rejection(server) if headers else nullcontext():
        connection = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=10)
        try:
            connection.putrequest("POST", "/api/editor", skip_host=True)
            for name, value in [("Host", server.host), ("Origin", server.origin),
                                ("Cookie", "evidence_connection=" + server.session),
                                ("X-CSRF-Token", server.csrf), ("Content-Type", "application/json"),
                                ("Content-Length", str(len(body))), *headers]:
                connection.putheader(name, value)
            connection.endheaders(body)
            response = connection.getresponse()
            response.read()
            assert response.status in (400, 403, 422)
        finally:
            connection.close()
    assert server.workspace.state()["revision"] == "empty"


def test_http_dictionary_editor_review_and_stale_write(server):
    example = json.loads(request(server, "/api/example")[2])
    status, _, raw = request(server, "/api/import", {"expectedRevision": "empty", **example})
    assert status == 200
    state = json.loads(raw)
    draft = deepcopy(state["ontology"])
    draft["entityTypes"][0]["description"] = "브라우저에서 편집한 합성 설명입니다."
    status, _, raw = request(server, "/api/editor", {"expectedRevision": state["revision"], "ontology": draft})
    assert status == 200
    edited = json.loads(raw)
    assert request(server, "/api/editor", {"expectedRevision": state["revision"], "ontology": draft})[0] == 409
    claim = edited["inspection"]["claims"][0]
    status, _, raw = request(server, "/api/review", {"expectedRevision": edited["revision"], "claimId": claim["id"], "basis": claim["basis"], "action": "accept", "actor": "Synthetic reviewer"})
    assert status == 200 and json.loads(raw)["inspection"]["claims"][0]["eligibility"] == "eligible"
    report_status, headers, report = request(server, "/report")
    assert report_status == 200 and "unsafe-inline" in headers["Content-Security-Policy"]
    assert draft["entityTypes"][0]["description"].encode() in report
    exported = json.loads(request(server, "/api/export")[2])
    assert exported["source"]["content"] == example["content"]
    assert exported["ontology"] == draft


def test_packaged_workbench_has_no_inline_executable_code():
    html = files("evidence_wiki").joinpath("web/workbench.html").read_text(encoding="utf-8")
    script = files("evidence_wiki").joinpath("web/workbench.js").read_text(encoding="utf-8")
    assert '<script src="/assets/workbench.js" defer></script>' in html
    assert "innerHTML" not in script
    assert "fatal: true, ignoreBOM: true" in script
    assert "https://" not in script
