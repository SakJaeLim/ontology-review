from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import sqlite3

from . import rules
from .inputs import (EvidenceError, LocalFile, MAX_RULE_BYTES, digest_json, load_manifest,
                     read_local, safe_path, workspace_root)


LIMITATIONS = [
    "This is an offline sidecar. It does not enforce decisions in the upstream wiki or factlog engine.",
    "Full-file changes require re-review. This is conservative dependency checking, not semantic impact analysis.",
    "SHACL conformance checks a small local property-constraint profile. It does not prove a claim is true.",
    "Only observed revisions are tracked. Edits made and reverted between inspections cannot be detected.",
    "Reviewer names are local assertions. The workspace is not an authenticated or tamper-proof audit system.",
    "This report is a captured snapshot. Reinspect the workspace before using an approval.",
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


class EvidenceWorkspace:
    def __init__(self, root: Path):
        self.root = workspace_root(Path(root))
        state_dir = safe_path(self.root, ".evidence-review")
        state_dir.mkdir(exist_ok=True)
        self.database = safe_path(self.root, ".evidence-review/state.sqlite3")
        for suffix in ("-journal", "-wal", "-shm"):
            safe_path(self.root, ".evidence-review/state.sqlite3" + suffix)
        with self._transaction() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS observations (
                    revision INTEGER PRIMARY KEY AUTOINCREMENT,
                    resource TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,
                    observed_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS observations_resource ON observations(resource, revision);
                CREATE TABLE IF NOT EXISTS decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    claim_id TEXT NOT NULL,
                    action TEXT NOT NULL CHECK(action IN ('accept', 'reject')),
                    actor TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    basis TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS decisions_claim ON decisions(claim_id, id);
            """)

    @classmethod
    def open(cls, root: Path) -> "EvidenceWorkspace":
        return cls(root)

    @contextmanager
    def _transaction(self):
        for suffix in ("", "-journal", "-wal", "-shm"):
            path = safe_path(self.root, ".evidence-review/state.sqlite3" + suffix)
            if path.exists() and path.stat().st_nlink > 1:
                raise EvidenceError("unsafe_state", "Review-state files must not have additional hard links.")
        db = sqlite3.connect(self.database, timeout=10, isolation_level=None)
        db.row_factory = sqlite3.Row
        try:
            db.execute("PRAGMA foreign_keys = ON")
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def _observe(db: sqlite3.Connection, resource: str, fingerprint: str, at: str) -> int:
        previous = db.execute("SELECT revision, fingerprint FROM observations WHERE resource=? ORDER BY revision DESC LIMIT 1", (resource,)).fetchone()
        if previous and previous["fingerprint"] == fingerprint:
            return previous["revision"]
        row = db.execute("INSERT INTO observations(resource, fingerprint, observed_at) VALUES (?,?,?)", (resource, fingerprint, at))
        return row.lastrowid

    @staticmethod
    def _decisions(db: sqlite3.Connection, claim_id: str) -> list[dict]:
        return [dict(row) for row in db.execute("SELECT id, action, actor, recorded_at, basis FROM decisions WHERE claim_id=? ORDER BY id", (claim_id,))]

    def _inspect(self, db: sqlite3.Connection) -> dict:
        manifest = load_manifest(self.root)
        at = _now()
        policy = self._observe(db, "policy", digest_json(rules.POLICY_REVISION), at)
        observed_files: dict[tuple[str, int], tuple[LocalFile, int]] = {}

        def observe_file(path: str, limit: int) -> tuple[LocalFile, int]:
            key = (path, limit)
            if key not in observed_files:
                source = read_local(self.root, path, limit)
                revision = self._observe(db, f"file:{path}:{limit}", digest_json([source.availability, source.digest]), at)
                observed_files[key] = source, revision
            return observed_files[key]

        active_ids = {claim["id"] for claim in manifest["claims"]}
        for row in db.execute("SELECT DISTINCT resource FROM observations WHERE resource LIKE 'claim:%'").fetchall():
            if row["resource"][6:] not in active_ids:
                self._observe(db, row["resource"], digest_json({"removed": True}), at)

        claims = []
        for claim in manifest["claims"]:
            claim_revision = self._observe(db, "claim:" + claim["id"], digest_json(claim), at)
            reasons, evidence_items, rule_items = [], [], []
            valid_value = rules.valid_claim_value(claim)
            if not valid_value:
                reasons.append("invalid_claim_value")
            if not claim["evidence"]:
                reasons.append("evidence_unbound")
            for span in claim["evidence"]:
                source, revision = observe_file(span["path"], 1_048_576)
                actual_text = None
                status = "not_checked"
                if source.availability == "available":
                    try:
                        lines = source.content.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n").split("\n")
                        if lines and lines[-1] == "":
                            lines.pop()
                        if span["end_line"] <= len(lines):
                            actual_text = "\n".join(lines[span["start_line"] - 1:span["end_line"]])
                            expected = span["text"].replace("\r\n", "\n").replace("\r", "\n")
                            status = "matches" if actual_text == expected else "mismatch"
                        else:
                            status = "span_missing"
                    except UnicodeError:
                        status = "invalid_encoding"
                if status != "matches":
                    reasons.append("evidence_" + (status if source.availability == "available" else source.availability))
                evidence_items.append({
                    "path": span["path"], "start_line": span["start_line"], "end_line": span["end_line"],
                    "expected_text": span["text"], "actual_text": actual_text,
                    "availability": source.availability, "status": status, "digest": source.digest,
                    "revision": revision,
                })
            if not claim["rules"]:
                reasons.append("rules_unbound")
            for path in claim["rules"]:
                source, revision = observe_file(path, MAX_RULE_BYTES)
                check = {"status": "not_checked", "focus_count": 0, "messages": [f"Rule file is {source.availability}."]}
                if source.availability == "available":
                    if not valid_value:
                        check["messages"] = ["The claim value does not match its declared datatype."]
                    elif Path(path).suffix.lower() != ".ttl":
                        check["messages"] = ["Only local .ttl Turtle rule files are supported."]
                    else:
                        check = rules.check_rule(source.content, claim)
                if check["status"] != "conforms":
                    reasons.append("rule_" + (check["status"] if source.availability == "available" else source.availability))
                rule_items.append({"path": path, "availability": source.availability, "digest": source.digest, "revision": revision, **check})
            basis = digest_json({
                "claim": [claim["id"], claim_revision], "policy": [rules.POLICY_REVISION, policy],
                "evidence": [[item["path"], item["revision"], item["status"]] for item in evidence_items],
                "rules": [[item["path"], item["revision"], item["status"]] for item in rule_items],
            })
            decisions = self._decisions(db, claim["id"])
            current = decisions[-1] if decisions else None
            if not current:
                review_state, eligibility = "unreviewed", "blocked" if reasons else "unreviewed"
                reasons.append("no_review")
            elif current["action"] == "reject":
                review_state, eligibility = "rejected", "blocked"
                reasons.append("review_rejected")
                if current["basis"] != basis:
                    reasons.append("basis_changed")
            elif current["basis"] != basis or reasons:
                review_state, eligibility = "needs_review", "blocked"
                if current["basis"] != basis:
                    reasons.append("basis_changed")
            else:
                review_state, eligibility = "approved", "eligible"
            claims.append({
                **{key: claim[key] for key in ("id", "title", "subject", "predicate", "value", "datatype", "wiki_pages")},
                "basis": basis, "review_state": review_state, "eligibility": eligibility,
                "reason_codes": sorted(set(reasons)), "evidence": evidence_items,
                "rules": rule_items, "decisions": decisions,
            })
        return {
            "schema_version": 1, "observed_at": at, "workspace_name": manifest.get("name", self.root.name),
            "claims": claims,
            "affected_pages": sorted({page for claim in claims if claim["eligibility"] == "blocked" for page in claim["wiki_pages"]}),
            "limitations": LIMITATIONS,
        }

    def inspect(self) -> dict:
        with self._transaction() as db:
            return self._inspect(db)

    def review(self, claim_id: str, action: str, *, basis: str, actor: str) -> dict:
        if action not in ("accept", "reject"):
            raise EvidenceError("invalid_action", "Review action must be accept or reject.")
        if not isinstance(actor, str) or not actor.strip() or len(actor) > 200:
            raise EvidenceError("invalid_actor", "A nonempty reviewer name of at most 200 characters is required.")
        with self._transaction() as db:
            inspection = self._inspect(db)
            claim = next((item for item in inspection["claims"] if item["id"] == claim_id), None)
            if claim is None:
                error = EvidenceError("unknown_claim", "The claim is not in the current manifest.")
            elif not isinstance(basis, str) or claim["basis"] != basis:
                error = EvidenceError("stale_basis", "The inspected basis has changed. Inspect and review the current evidence.")
            elif action == "accept" and any(reason not in ("no_review", "basis_changed", "review_rejected") for reason in claim["reason_codes"]):
                error = EvidenceError("checks_failed", "Acceptance requires every evidence span and rule check to pass.")
            else:
                error = None
                latest = claim["decisions"][-1] if claim["decisions"] else None
                inserted_id = None
                if not latest or (latest["action"], latest["actor"], latest["basis"]) != (action, actor.strip(), basis):
                    inserted_id = db.execute("INSERT INTO decisions(claim_id, action, actor, recorded_at, basis) VALUES (?,?,?,?,?)", (claim_id, action, actor.strip(), _now(), basis)).lastrowid
                inspection = self._inspect(db)
                checked = next((item for item in inspection["claims"] if item["id"] == claim_id), None)
                if checked is None or checked["basis"] != basis:
                    if inserted_id is not None:
                        db.execute("DELETE FROM decisions WHERE id=?", (inserted_id,))
                    error = EvidenceError("stale_basis", "The basis changed during review. Inspect the current evidence.")
        if error is not None:
            raise error
        return inspection
