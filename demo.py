"""Reproduce four evidence-review stages using synthetic local files."""

import argparse
import json
from pathlib import Path
import shutil
import sys

from evidence_wiki import EvidenceError, EvidenceWorkspace
from evidence_wiki.inputs import workspace_root


FIXTURE = Path(__file__).parent / "examples" / "synthetic"


def run_demo(destination: Path, *, render: bool = True) -> dict:
    destination = destination.absolute()
    if destination.exists():
        workspace_root(destination)
        if any(destination.iterdir()):
            raise EvidenceError("output_not_empty", "The demo requires a new or empty output directory.")
    else:
        workspace_root(destination.parent)
        destination.mkdir()
    root = workspace_root(destination)
    shutil.copytree(FIXTURE, root, dirs_exist_ok=True)
    workspace = EvidenceWorkspace.open(root)
    bundle = {"schema_version": 1, "demo": True, "title": "Evidence review walkthrough", "stages": []}

    def capture(stage_id: str, ko: str, en: str, description_ko: str, description_en: str) -> dict:
        inspection = workspace.inspect()
        bundle["stages"].append({"id": stage_id, "label_ko": ko, "label_en": en,
            "description_ko": description_ko, "description_en": description_en, "inspection": inspection})
        return inspection

    for claim in workspace.inspect()["claims"]:
        workspace.review(claim["id"], "accept", basis=claim["basis"], actor="Synthetic demo reviewer")
    initial = capture("approved", "최초 검토", "Initial review",
        "가상 검토자가 두 주장에 근거와 규칙을 확인한 뒤 승인했습니다.",
        "A synthetic reviewer accepted both claims after checking their evidence and rules.")
    assert all(claim["eligibility"] == "eligible" for claim in initial["claims"])
    source = root / "sources" / "retention.md"
    source.write_text(source.read_text(encoding="utf-8").replace("30 days", "90 days"), encoding="utf-8")
    changed = capture("source_changed", "원문 변경", "Source changed",
        "원문은 90일로 바뀌었습니다. 30일 주장의 과거 승인은 남지만 현재 사용은 막힙니다.",
        "The source now says 90 days. The 30-day approval remains in history but is no longer eligible.")
    assert changed["claims"][0]["review_state"] == "needs_review"
    assert changed["affected_pages"] == ["wiki/retention.md"]
    manifest_path = root / "workspace.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["claims"][0]["value"] = 90
    manifest["claims"][0]["evidence"][0]["text"] = "SyntheticProject retains records for 90 days."
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    violation = capture("rule_violation", "규칙 위반", "Rule violation",
        "주장과 인용을 90일로 갱신했습니다. 실제 SHACL 검사는 상한 60일 위반을 판정합니다.",
        "The claim and quote now say 90 days. Actual SHACL validation reports a violation of the 60-day maximum.")
    assert violation["claims"][0]["rules"][0]["status"] == "violates"
    rule = root / "rules" / "retention.ttl"
    rule.write_text(rule.read_text(encoding="utf-8").replace("sh:maxInclusive 60", "sh:maxInclusive 120"), encoding="utf-8")
    pending = workspace.inspect()["claims"][0]
    assert pending["rules"][0]["status"] == "conforms" and pending["eligibility"] == "blocked"
    workspace.review("retention", "accept", basis=pending["basis"], actor="Synthetic demo reviewer")
    final = capture("reviewed_again", "재검토 승인", "Reviewed again",
        "상한을 120일로 바꾼 뒤 가상 검토자가 현재 근거로 다시 승인했습니다. 담당 조직의 승인은 유지됩니다.",
        "After changing the maximum to 120 days, the synthetic reviewer accepted the current basis. The owner approval remains eligible.")
    assert all(claim["eligibility"] == "eligible" for claim in final["claims"])
    assert len(final["claims"][0]["decisions"]) == 2
    assert all(stage["inspection"]["claims"][1]["eligibility"] == "eligible" for stage in bundle["stages"])
    (root / "demo.json").write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
    if render:
        from evidence_wiki.report import render_report
        render_report(bundle, root / "index.html", language="ko")
        render_report(bundle, root / "index.en.html", language="en")
    return bundle


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        bundle = run_demo(args.output)
        print(json.dumps({"output": str(args.output.absolute()), "stages": [
            {"id": stage["id"], "eligible": sum(claim["eligibility"] == "eligible" for claim in stage["inspection"]["claims"]),
             "blocked": sum(claim["eligibility"] == "blocked" for claim in stage["inspection"]["claims"])}
            for stage in bundle["stages"]]}, ensure_ascii=False, indent=2))
        return 0
    except (EvidenceError, OSError) as exc:
        print(json.dumps({"error": getattr(exc, "code", "io_error"), "message": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
