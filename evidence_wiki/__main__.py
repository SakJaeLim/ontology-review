import argparse
import json
from pathlib import Path
import sqlite3
import sys

from .inputs import EvidenceError, import_factlog, new_output_path, workspace_root
from .workspace import EvidenceWorkspace


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Review source-bound claims using local evidence and SHACL rules.")
    commands = parser.add_subparsers(dest="command", required=True)
    inspect = commands.add_parser("inspect", help="Observe revisions and print the current review snapshot.")
    inspect.add_argument("workspace", type=Path)
    inspect.add_argument("--json", dest="json_path", help="New JSON output path relative to the workspace.")
    inspect.add_argument("--html", dest="html_path", help="New HTML output path relative to the workspace.")
    inspect.add_argument("--language", choices=("ko", "en"), default="ko")
    review = commands.add_parser("review", help="Accept or reject the exact inspected basis.")
    review.add_argument("workspace", type=Path)
    review.add_argument("claim_id")
    review.add_argument("action", choices=("accept", "reject"))
    review.add_argument("--basis", required=True)
    review.add_argument("--actor", required=True)
    importer = commands.add_parser("import-factlog", help="Export unreviewed drafts from a seven-column factlog CSV.")
    importer.add_argument("workspace", type=Path)
    importer.add_argument("input", help="CSV path relative to the workspace.")
    importer.add_argument("--out", required=True, help="New draft JSON path relative to the workspace.")
    args = parser.parse_args(argv)
    try:
        if args.command == "import-factlog":
            root = workspace_root(args.workspace)
            destination = new_output_path(root, args.out)
            report = import_factlog(root, args.input)
            with destination.open("x", encoding="utf-8") as stream:
                json.dump(report, stream, ensure_ascii=False, indent=2)
        else:
            workspace = EvidenceWorkspace.open(args.workspace)
            if args.command == "review":
                report = workspace.review(args.claim_id, args.action, basis=args.basis, actor=args.actor)
            else:
                destinations = {key: new_output_path(workspace.root, value) for key, value in (("json", args.json_path), ("html", args.html_path)) if value}
                if len(set(destinations.values())) != len(destinations):
                    raise EvidenceError("invalid_output", "JSON and HTML output paths must differ.")
                report = workspace.inspect()
                if "json" in destinations:
                    with destinations["json"].open("x", encoding="utf-8") as stream:
                        json.dump(report, stream, ensure_ascii=False, indent=2)
                if "html" in destinations:
                    from .report import render_report
                    render_report(report, destinations["html"], language=args.language)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except EvidenceError as exc:
        print(json.dumps({"error": exc.code, "message": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    except (OSError, sqlite3.Error) as exc:
        print(json.dumps({"error": "io_error", "message": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 3


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
