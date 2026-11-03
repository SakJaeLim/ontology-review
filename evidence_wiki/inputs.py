from __future__ import annotations

import hashlib
import json
import math
import os
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import stat
import csv
import io
from urllib.parse import quote


MAX_FILE_BYTES = 1_048_576
MAX_RULE_BYTES = 65_536
MAX_CLAIMS = 200
XSD = "http://www.w3.org/2001/XMLSchema#"
DATATYPES = {XSD + name for name in ("string", "integer", "decimal", "boolean")}


class EvidenceError(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class LocalFile:
    availability: str
    digest: str | None = None
    content: bytes | None = None


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest_json(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _reparse(path: Path) -> bool:
    info = path.lstat()
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, "st_file_attributes", 0) & 0x400)


def workspace_root(root: Path) -> Path:
    lexical = root.absolute()
    try:
        if any(_reparse(p) for p in (lexical, *lexical.parents)):
            raise EvidenceError("unsafe_root", "Workspace ancestors must not be symbolic links or junctions.")
        resolved = lexical.resolve(strict=True)
    except OSError as exc:
        raise EvidenceError("invalid_root", "Workspace must be an existing directory.") from exc
    if not resolved.is_dir():
        raise EvidenceError("invalid_root", "Workspace must be an existing directory.")
    return resolved


def safe_path(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or len(relative) > 512:
        raise EvidenceError("unsafe_path", "A short workspace-relative file path is required.")
    posix, windows = PurePosixPath(relative), PureWindowsPath(relative)
    if ("\\" in relative or ":" in relative or "\x00" in relative or
            posix.is_absolute() or windows.is_absolute() or windows.drive or
            any(part in ("", ".", "..") for part in relative.split("/")) or
            any(part.endswith((" ", ".")) for part in posix.parts) or
            any(re.fullmatch(r"(?i)(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?", part)
                for part in posix.parts)):
        raise EvidenceError("unsafe_path", "Paths must stay within the workspace without links or traversal.")
    candidate = root.joinpath(*posix.parts)
    current = root
    for part in posix.parts:
        current = current / part
        try:
            if _reparse(current):
                raise EvidenceError("unsafe_path", "Symbolic links and junctions are not supported.")
        except FileNotFoundError:
            break
    if not candidate.resolve(strict=False).is_relative_to(root):
        raise EvidenceError("unsafe_path", "The path leaves the workspace.")
    return candidate


def read_local(root: Path, relative: str, limit: int = MAX_FILE_BYTES) -> LocalFile:
    try:
        path = safe_path(root, relative)
        before = path.stat()
        if not stat.S_ISREG(before.st_mode):
            return LocalFile("unreadable")
        if before.st_size > limit:
            return LocalFile("too_large")
        with path.open("rb") as stream:
            opened = os.fstat(stream.fileno())
            safe_path(root, relative)
            if (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino):
                return LocalFile("unstable")
            content = stream.read(limit + 1)
            after = os.fstat(stream.fileno())
        if len(content) > limit:
            return LocalFile("too_large")
        if (opened.st_size, opened.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            return LocalFile("unstable")
        return LocalFile("available", hashlib.sha256(content).hexdigest(), content)
    except EvidenceError:
        return LocalFile("unsafe")
    except FileNotFoundError:
        return LocalFile("missing")
    except (OSError, ValueError, RuntimeError):
        return LocalFile("unreadable")


def _text(value: object, field: str, *, max_length: int = 4096) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > max_length:
        raise EvidenceError("invalid_manifest", f"{field} must be a nonempty bounded string.")
    return value


def _iri(value: object, field: str) -> str:
    value = _text(value, field)
    if not re.fullmatch(r"(?:https?://|urn:)[^\s<>\"{}|\\^`]+", value):
        raise EvidenceError("invalid_manifest", f"{field} must be an absolute http, https, or urn IRI.")
    return value


def _unique_keys(pairs: list) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise EvidenceError("invalid_manifest", "Duplicate JSON keys are not allowed.")
        result[key] = value
    return result


def load_manifest(root: Path) -> dict:
    source = read_local(root, "workspace.json")
    if source.availability != "available":
        raise EvidenceError("manifest_unavailable", f"workspace.json is {source.availability}.")
    try:
        manifest = json.loads(source.content.decode("utf-8"), object_pairs_hook=_unique_keys,
                              parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
        canonical_json(manifest).encode("utf-8")
    except (ValueError, UnicodeError, RecursionError) as exc:
        if isinstance(exc, EvidenceError):
            raise
        raise EvidenceError("invalid_manifest", "workspace.json must contain valid UTF-8 JSON.") from exc
    if not isinstance(manifest, dict) or type(manifest.get("schema_version")) is not int or manifest["schema_version"] != 1:
        raise EvidenceError("invalid_manifest", "Expected manifest schema_version 1.")
    claims = manifest.get("claims")
    if not isinstance(claims, list) or len(claims) > MAX_CLAIMS:
        raise EvidenceError("invalid_manifest", f"claims must be an array of at most {MAX_CLAIMS} items.")
    if "name" in manifest:
        _text(manifest["name"], "name", max_length=200)
    ids = set()
    for claim in claims:
        if not isinstance(claim, dict):
            raise EvidenceError("invalid_manifest", "Each claim must be an object.")
        claim_id = _text(claim.get("id"), "id", max_length=120)
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", claim_id) or claim_id in ids:
            raise EvidenceError("invalid_manifest", "Claim ids must be unique ASCII identifiers.")
        ids.add(claim_id)
        _text(claim.get("title"), "title", max_length=500)
        _iri(claim.get("subject"), "subject")
        _iri(claim.get("predicate"), "predicate")
        if not isinstance(claim.get("datatype"), str) or claim["datatype"] not in DATATYPES:
            raise EvidenceError("invalid_manifest", "Unsupported claim datatype.")
        value = claim.get("value")
        if type(value) not in (str, int, float, bool) or (isinstance(value, str) and len(value) > 16_384):
            raise EvidenceError("invalid_manifest", "Claim value must be a bounded scalar.")
        if isinstance(value, float) and not math.isfinite(value):
            raise EvidenceError("invalid_manifest", "Non-finite claim values are not allowed.")
        for key, maximum in (("evidence", 10), ("rules", 10), ("wiki_pages", 30)):
            if not isinstance(claim.get(key), list) or len(claim[key]) > maximum:
                raise EvidenceError("invalid_manifest", f"{key} must be a bounded array.")
        for evidence in claim["evidence"]:
            if not isinstance(evidence, dict):
                raise EvidenceError("invalid_manifest", "Each evidence span must be an object.")
            _text(evidence.get("path"), "evidence.path", max_length=512)
            _text(evidence.get("text"), "evidence.text", max_length=16_384)
            start, end = evidence.get("start_line"), evidence.get("end_line")
            if type(start) is not int or type(end) is not int or not 1 <= start <= end <= 100_000:
                raise EvidenceError("invalid_manifest", "Evidence spans require inclusive positive line numbers.")
        for path in claim["rules"]:
            _text(path, "rules.path", max_length=512)
        for page in claim["wiki_pages"]:
            _text(page, "wiki_pages", max_length=512)
    return manifest


def import_factlog(root: Path, relative: str) -> dict:
    source = read_local(root, relative)
    if source.availability != "available":
        raise EvidenceError("import_unavailable", f"Input CSV is {source.availability}.")
    fields = ["subject", "relation", "object", "source", "status", "confidence", "note"]
    try:
        reader = csv.DictReader(io.StringIO(source.content.decode("utf-8-sig")), strict=True)
        if reader.fieldnames != fields:
            raise EvidenceError("invalid_import", "Expected factlog's exact seven-column CSV header.")
        claims = []
        for index, row in enumerate(reader, start=1):
            if index > MAX_CLAIMS or set(row) != set(fields) or any(not isinstance(value, str) or len(value) > 4096 for value in row.values()):
                raise EvidenceError("invalid_import", "Invalid or oversized factlog CSV row.")
            claims.append({
                "id": f"factlog-{index:04d}", "title": f"{row['subject']} {row['relation']}"[:500],
                "subject": "urn:factlog:entity:" + quote(row["subject"], safe=""),
                "predicate": "urn:factlog:relation:" + quote(row["relation"], safe=""),
                "value": row["object"], "datatype": XSD + "string",
                "evidence": [], "rules": [], "wiki_pages": [],
                "external_record": row,
            })
        return {"schema_version": 1, "name": "Imported factlog drafts", "claims": claims}
    except (UnicodeError, csv.Error) as exc:
        raise EvidenceError("invalid_import", "Input must be a valid UTF-8 seven-column CSV.") from exc


def new_output_path(root: Path, relative: str) -> Path:
    if relative.split("/")[0].casefold() == ".evidence-review":
        raise EvidenceError("invalid_output", "The internal review-state directory is reserved.")
    destination = safe_path(root, relative)
    if destination.exists():
        raise EvidenceError("output_exists", "Choose a new output path; existing files are not overwritten.")
    if not destination.parent.is_dir():
        raise EvidenceError("invalid_output", "The output directory must already exist inside the workspace.")
    return destination
