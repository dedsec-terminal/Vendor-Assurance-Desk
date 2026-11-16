#!/usr/bin/env python3
"""Build a provenance-linked, synthetic-scope outcome scorecard."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_json_sha256(path: Path) -> str:
    """Hash parsed JSON canonically so CRLF/LF checkout conversion is irrelevant."""
    import hashlib
    canonical = json.dumps(read_json(path), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _platform_snapshot(path: Path, assessment: dict[str, Any], source_hashes: dict[str, str] | None = None) -> dict[str, Any]:
    if not path.exists():
        return {"status": "pending", "reason": "No platform_sync.json snapshot is available.", "counts": None}
    snap = read_json(path)
    expected = {"case_id": assessment.get("case_id"), "input_sha256": assessment.get("input_sha256"),
                "vendor_id": assessment.get("vendor", {}).get("vendor_id")}
    mismatches = {key: {"expected": value, "actual": snap.get(key)} for key, value in expected.items()
                  if value is not None and snap.get(key) != value}
    expected_sources = source_hashes or {}
    actual_sources = snap.get("source_file_sha256", {})
    if expected_sources and snap.get("source_hash_format") != "canonical-json-v1":
        mismatches["source_hash_format"] = {"expected": "canonical-json-v1", "actual": snap.get("source_hash_format")}
    for filename, value in expected_sources.items():
        actual = actual_sources.get(filename)
        if actual != value:
            mismatches[f"source_file_sha256.{filename}"] = {"expected": value, "actual": actual}
    # These IDs must exist to safely attribute a round-trip count to this case.
    missing = [key for key in ("service_id", "assessment_id") if not snap.get(key)]
    if mismatches or missing:
        return {"status": "invalid", "reason": "Snapshot identity/provenance did not match this assessment.",
                "mismatches": mismatches, "missing_identity_fields": missing, "counts": None}
    counts = snap.get("link_counts") or snap.get("counts")
    links_verified = snap.get("links_verified") is True or snap.get("verification_status") == "verified"
    if not isinstance(counts, dict) or not links_verified:
        return {"status": "pending", "reason": "Matching platform snapshot exists, but verified linked-record counts are absent.",
                "service_id": snap["service_id"], "assessment_id": snap["assessment_id"], "counts": None}
    required = ("vendor", "service", "assessment", "applied_controls", "findings", "evidence",
                "unique_applied_controls", "supplier_scope_controls")
    if any(not isinstance(counts.get(key), int) or counts[key] < 0 for key in required):
        return {"status": "invalid", "reason": "Platform linked-record counts must be non-negative integers.",
                "service_id": snap["service_id"], "assessment_id": snap["assessment_id"], "counts": None}
    return {"status": "verified", "reason": "Identity and input hash match; platform worker verified the linked records.",
            "service_id": snap["service_id"], "assessment_id": snap["assessment_id"],
            "evidence_sha256": snap.get("evidence_sha256"), "counts": {key: counts[key] for key in required}}


def build(assessment: dict[str, Any], review: dict[str, Any], platform_path: Path,
          source_hashes: dict[str, str] | None = None) -> dict[str, Any]:
    baseline = {c["check_id"]: c for c in assessment["checks"]["baseline"]}
    retest = {c["check_id"]: c for c in assessment["checks"]["retest"]}
    if set(baseline) != set(retest):
        raise ValueError("Baseline and retest check IDs differ; cannot calculate a comparable delta.")
    metadata = []
    for cid, first in baseline.items():
        last = retest[cid]
        metadata.append({"check_id": cid, "baseline": first["result"], "retest": last["result"],
                         "gap_delta": int(last["result"] == "gap") - int(first["result"] == "gap"),
                         "baseline_evidence_id": first["evidence_id"], "baseline_evidence_sha256": first.get("evidence_sha256"),
                         "retest_evidence_id": last["evidence_id"], "retest_evidence_sha256": last.get("evidence_sha256")})
    findings = assessment.get("findings", [])
    coverage = {"findings": len(findings),
                "owner_present": sum(bool(x.get("owner")) for x in findings),
                "due_date_present": sum(bool(x.get("due_date")) for x in findings),
                "evidence_hash_present": sum(bool(x.get("evidence_sha256")) and bool(x.get("retest_evidence_sha256")) for x in findings)}
    itgc = review.get("tests", {}).get("controls", [])
    baseline_exc = sum(int(c.get("baseline_exception_count", 0)) for c in itgc)
    retest_exc = sum(int(c.get("retest_count", 0)) for c in itgc)
    unresolved_current = sum(not bool(c.get("current_exposure_resolved")) for c in itgc)
    historical = sum(len(c.get("retest_exceptions", [])) for c in itgc)
    old_current = sum(not bool(x.get("current_exposure_resolved", False)) for c in itgc for x in c.get("baseline_exceptions", []))
    # Independently validate non-negative integral counts before reporting deltas.
    for label, value in (("baseline_exception_count", baseline_exc), ("retest_exception_count", retest_exc)):
        if not isinstance(value, int) or value < 0:
            raise ValueError(f"Invalid {label}")
    return {
        "case_id": assessment["case_id"], "input_sha256": assessment["input_sha256"],
        "scope": {"vendors": 1, "metadata_checks": len(metadata), "itgc_controls": len(itgc),
                  "synthetic_only": True, "overall_maturity_score": None},
        "metadata_check_outcomes": {"baseline_gaps": sum(x["baseline"] == "gap" for x in metadata),
                                    "retest_gaps": sum(x["retest"] == "gap" for x in metadata),
                                    "gap_delta": sum(x["gap_delta"] for x in metadata), "checks": metadata},
        "finding_follow_up_coverage": coverage,
        "itgc_outcomes": {"baseline_exception_count": baseline_exc, "retest_exception_count": retest_exc,
                          "exception_delta": retest_exc - baseline_exc, "current_exposures_unresolved": unresolved_current,
                          "historical_exceptions_preserved": historical,
                          "current_exposures_unresolved_at_baseline": old_current,
                          "controls": [{"control_id": c["id"], "baseline_exceptions": c.get("baseline_exception_count", 0),
                                        "retest_exceptions": c.get("retest_count", 0),
                                        "current_exposure_resolved": c.get("current_exposure_resolved"),
                                        "historical_exception_ids": [e.get("record_id") for e in c.get("retest_exceptions", [])]}
                                       for c in itgc]},
        "human_review": {"status": assessment.get("communication", {}).get("feedback_status", "Pending"),
                         "reviewer_closures": assessment.get("metrics", {}).get("reviewer_closures", 0),
                         "onboarding_decision": assessment.get("recommendation", {}).get("human_approval", "Pending")},
        "platform_roundtrip": _platform_snapshot(platform_path, assessment, source_hashes),
        "limitations": ["All records are fictional training data.",
                        "One vendor, four selected metadata checks, and three small ITGC tests only.",
                        "Passing a selected retest is not authentication, assurance, operating-effectiveness evidence, or approval.",
                        "Counts describe this fixture only; no time savings, risk reduction, or business outcome is inferred."]
    }


def render_markdown(data: dict[str, Any]) -> str:
    m, i, p = data["metadata_check_outcomes"], data["itgc_outcomes"], data["platform_roundtrip"]
    lines = ["# Synthetic outcome scorecard", "", f"**Case:** `{data['case_id']}`<br>",
             f"**Assessment input SHA-256:** `{data['input_sha256']}`", "",
             "> Training fixture only: one fictional vendor, four selected metadata checks and three small ITGC tests. No overall maturity score is calculated.", "",
             "## Assurance metadata retest", "",
             f"Selected checks with a gap: **{m['baseline_gaps']}/4 baseline → {m['retest_gaps']}/4 retest** (net gap delta **{m['gap_delta']:+d}**). This is a change in fixture check results, not a risk reduction claim.", "",
             "| Check | Baseline | Retest | Evidence (baseline → retest) |", "|---|---|---|---|"]
    lines += [f"| {x['check_id']} | {x['baseline']} | {x['retest']} | `{x['baseline_evidence_id']}` → `{x['retest_evidence_id']}` |" for x in m["checks"]]
    c = data["finding_follow_up_coverage"]
    lines += ["", "## Finding follow-up fields", "", f"Owner present: **{c['owner_present']}/{c['findings']}** · due date present: **{c['due_date_present']}/{c['findings']}** · baseline and retest evidence hashes present: **{c['evidence_hash_present']}/{c['findings']}**.", "",
              "## ITGC exception retest", "", f"Exceptions: **{i['baseline_exception_count']} baseline → {i['retest_exception_count']} retest** (delta **{i['exception_delta']:+d}**). Current exposure remains unresolved in **{i['current_exposures_unresolved']}/{data['scope']['itgc_controls']}** selected control(s); **{i['historical_exceptions_preserved']}** historical exception record(s) remain in the retest history.", "",
              "| Control | Baseline exceptions | Retest exceptions | Current exposure resolved | Historical exception IDs |", "|---|---:|---:|---|---|"]
    lines += [f"| {x['control_id']} | {x['baseline_exceptions']} | {x['retest_exceptions']} | {x['current_exposure_resolved']} | {', '.join(x['historical_exception_ids']) or '—'} |" for x in i["controls"]]
    lines += ["", "## GRC platform record links", "", f"Status: **{p['status']}** — {p['reason']}"]
    if p.get("counts"):
        lines += ["", "| Platform measure | Count |", "|---|---:|"]
        descriptions = {"vendor": "Vendor records", "service": "Service records", "assessment": "Assessment records",
                        "applied_controls": "Finding-to-control link relationships (not unique controls)",
                        "findings": "Linked finding records", "evidence": "Linked evidence records",
                        "unique_applied_controls": "Distinct configured control records represented by those links",
                        "supplier_scope_controls": "Total supplier-scope control records configured for the assessment"}
        lines += [f"| {descriptions[k]} | {v} |" for k, v in p["counts"].items()]
        lines += ["", "Finding-to-control link count is separate from distinct configured controls and total supplier-scope controls."]
    lines += ["", "## Human review", "", f"Peer feedback: **{data['human_review']['status']}** · reviewer closures: **{data['human_review']['reviewer_closures']}** · final onboarding decision: **{data['human_review']['onboarding_decision']}**.", "",
              "## Scope and limits", ""] + [f"- {x}" for x in data["limitations"]]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root
    assessment_path = root / "output/assessment.json"
    review_path = root / "output/control_review.json"
    source_hashes = {path.name: canonical_json_sha256(path) for path in (assessment_path, review_path)}
    score = build(read_json(assessment_path), read_json(review_path), root / "output/platform_sync.json", source_hashes)
    (root / "output/outcome_scorecard.json").write_text(json.dumps(score, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (root / "output/outcome_scorecard.md").write_text(render_markdown(score), encoding="utf-8")


if __name__ == "__main__":
    main()
