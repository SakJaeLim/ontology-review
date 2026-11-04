from __future__ import annotations

from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
import json
import mimetypes
from pathlib import Path
import secrets
import sqlite3
import tempfile
from urllib.parse import unquote, urlsplit

from .connection import ConnectionWorkspace, PROTOCOL, _bounded, _unique_pairs
from .inputs import EvidenceError, safe_path, workspace_root
from .report import render_report


MAX_BODY_BYTES = 4_194_304
COOKIE = "evidence_connection"
ASSETS = {
    "workbench.js": ("web/workbench.js", "text/javascript; charset=utf-8"),
    "workbench.css": ("web/workbench.css", "text/css; charset=utf-8"),
    "open-props.css": ("design/open-props.css", "text/css; charset=utf-8"),
    "files.svg": ("design/files.svg", "image/svg+xml"),
    "LICENSE.open-props": ("design/LICENSE.open-props", "text/plain; charset=utf-8"),
    "LICENSE.lucide": ("design/LICENSE.lucide", "text/plain; charset=utf-8"),
}
COMMANDS = {
    "/api/import": ("import_dictionary", {"expectedRevision", "filename", "content"}),
    "/api/editor": ("save_editor", {"expectedRevision", "ontology"}),
    "/api/review": ("review", {"expectedRevision", "claimId", "basis", "action", "actor"}),
}


class ConnectionServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, workspace: ConnectionWorkspace, editor_dist: Path, port: int = 8770):
        self.workspace = workspace
        self.editor_dist = workspace_root(editor_dist)
        if not safe_path(self.editor_dist, "index.html").is_file():
            raise EvidenceError("invalid_editor", "The editor directory must contain the built index.html.")
        self.session = secrets.token_urlsafe(32)
        self.csrf = secrets.token_urlsafe(32)
        super().__init__(("127.0.0.1", port), ConnectionHandler)
        self.host = f"127.0.0.1:{self.server_address[1]}"
        self.origin = "http://" + self.host


class ConnectionHandler(BaseHTTPRequestHandler):
    server: ConnectionServer

    def setup(self):
        super().setup()
        self.connection.settimeout(15)

    def log_message(self, format, *args):
        pass

    def _send(self, status, content, content_type="application/json; charset=utf-8", *, cookie=False, report=False):
        if isinstance(content, dict):
            content = json.dumps(content, ensure_ascii=False, allow_nan=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        policy = ("default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'" if report else
                  "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; font-src 'self' data:")
        self.send_header("Content-Security-Policy", policy + "; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'self'")
        if cookie:
            self.send_header("Set-Cookie", f"{COOKIE}={self.server.session}; HttpOnly; SameSite=Strict; Path=/")
        self.end_headers()
        self.wfile.write(content)

    def _error(self, error, status=None):
        if status is None:
            status = 409 if error.code in {"stale_revision", "stale_basis", "source_integrity", "no_dictionary"} else 422
        self._send(status, {"error": error.code, "message": str(error)})

    def _boundary(self, *, mutation=False):
        hosts = self.headers.get_all("Host", [])
        if hosts != [self.server.host]:
            raise EvidenceError("forbidden_host", "Use the exact loopback address shown by the server.")
        origins = self.headers.get_all("Origin", [])
        if origins and origins != [self.server.origin]:
            raise EvidenceError("forbidden_origin", "Only this local workbench origin is accepted.")
        if self.headers.get("Sec-Fetch-Site") == "cross-site":
            raise EvidenceError("forbidden_origin", "Cross-site requests are not accepted.")
        if mutation and origins != [self.server.origin]:
            raise EvidenceError("forbidden_origin", "A same-origin request is required.")

    def _authenticated(self, *, mutation=False):
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get("Cookie", ""))
            value = cookie[COOKIE].value if COOKIE in cookie else ""
        except Exception as exc:
            raise EvidenceError("invalid_session", "Open the local workbench to start a session.") from exc
        if not secrets.compare_digest(value, self.server.session):
            raise EvidenceError("invalid_session", "Open the local workbench to start a session.")
        tokens = self.headers.get_all("X-CSRF-Token", [])
        if mutation and (len(tokens) != 1 or not secrets.compare_digest(tokens[0], self.server.csrf)):
            raise EvidenceError("invalid_csrf", "Reload the local workbench session before saving.")

    def do_GET(self):
        try:
            self._boundary()
            target = urlsplit(self.path)
            path = unquote(target.path, errors="strict")
            if path == "/api/session":
                self._send(200, {"connected": True, "protocol": PROTOCOL, "csrfToken": self.server.csrf}, cookie=True)
                return
            if path.startswith("/api/") or path == "/report":
                self._authenticated()
            if path == "/api/state":
                self._send(200, self.server.workspace.state())
            elif path == "/api/export":
                self._send(200, self.server.workspace.export())
            elif path == "/api/example":
                content = files("evidence_wiki").joinpath("web/example.json").read_text(encoding="utf-8")
                self._send(200, {"filename": "synthetic-nvidia-dictionary.json", "content": content})
            elif path == "/report":
                state = self.server.workspace.state()
                if state["inspection"] is None:
                    raise EvidenceError("no_dictionary", "Import a dictionary before opening its report.")
                with tempfile.TemporaryDirectory(prefix="evidence-report-") as temporary:
                    destination = Path(temporary) / "report.html"
                    render_report(state["inspection"], destination)
                    self._send(200, destination.read_bytes(), "text/html; charset=utf-8", report=True)
            elif path == "/":
                self._send(200, files("evidence_wiki").joinpath("web/workbench.html").read_bytes(), "text/html; charset=utf-8")
            elif path.startswith("/assets/") and path[len("/assets/"):] in ASSETS:
                name, content_type = ASSETS[path[len("/assets/"):]]
                self._send(200, files("evidence_wiki").joinpath(name).read_bytes(), content_type)
            elif path.startswith("/editor/"):
                relative = path[len("/editor/"):] or "index.html"
                source = safe_path(self.server.editor_dist, relative)
                if not source.is_file() or source.stat().st_size > 20_971_520:
                    self._send(404, {"error": "not_found", "message": "Editor asset not found."})
                    return
                content_type = mimetypes.guess_type(source.name)[0] or "application/octet-stream"
                if source.suffix == ".js":
                    content_type = "text/javascript"
                self._send(200, source.read_bytes(), content_type)
            else:
                self._send(404, {"error": "not_found", "message": "Route not found."})
        except EvidenceError as exc:
            self._error(exc, 403 if exc.code in {"forbidden_host", "forbidden_origin", "invalid_session"} else None)
        except (OSError, sqlite3.Error, UnicodeError, ValueError, KeyError, TypeError):
            self._send(400, {"error": "unavailable", "message": "The local resource could not be read safely."})

    def do_POST(self):
        try:
            self._boundary(mutation=True)
            self._authenticated(mutation=True)
            if self.path not in COMMANDS:
                self._send(404, {"error": "not_found", "message": "Route not found."})
                return
            lengths = self.headers.get_all("Content-Length", [])
            if self.headers.get("Transfer-Encoding") or len(lengths) != 1 or not lengths[0].isdigit():
                self._send(400, {"error": "invalid_body", "message": "One bounded Content-Length is required."})
                return
            size = int(lengths[0])
            if not 0 < size <= MAX_BODY_BYTES:
                self._send(413, {"error": "body_too_large", "message": "The request exceeds its size limit."})
                return
            if self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json":
                self._send(415, {"error": "invalid_content_type", "message": "Use application/json."})
                return
            raw = self.rfile.read(size)
            if len(raw) != size:
                raise ValueError("Incomplete body")
            body = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_pairs,
                              parse_constant=lambda item: (_ for _ in ()).throw(ValueError(item)))
            if isinstance(body, dict):
                _bounded({key: value for key, value in body.items() if key != "content"})
            method, fields = COMMANDS[self.path]
            if not isinstance(body, dict) or set(body) != fields:
                self._send(400, {"error": "invalid_body", "message": "The request fields do not match this operation."})
                return
            self._send(200, getattr(self.server.workspace, method)(**body))
        except EvidenceError as exc:
            self._error(exc, 403 if exc.code in {"forbidden_host", "forbidden_origin", "invalid_session", "invalid_csrf"} else None)
        except (OSError, sqlite3.Error, UnicodeError, ValueError, TypeError, RecursionError):
            self._send(400, {"error": "invalid_body", "message": "The operation could not be completed safely."})


def serve(root: Path, editor_dist: Path, port: int = 8770):
    """Run a loopback-only workspace and a separately built Microsoft editor."""
    with ConnectionServer(ConnectionWorkspace(root), editor_dist, port) as server:
        print(f"Ontology workbench: {server.origin}/", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
