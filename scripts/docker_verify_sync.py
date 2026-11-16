"""Read-only verification of the synthetic CISO Assistant assessment sync."""
from __future__ import annotations
import hashlib
import json
import os
import sys
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, "/code")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ciso_assistant.settings")
import django
with redirect_stdout(sys.stderr):
    django.setup()

from core.models import AppliedControl, Evidence, Finding, FindingsAssessment
from tprm.models import Entity, EntityAssessment, Solution

BASE = Path("/code/db/vad_data")
PREFIX = "VAD-SYN-HPD-"
EXPECTED = {"CERT-EXPIRY": {"TPRM-REV-01"}, "ASSURANCE-SCOPE": {"TPRM-REV-01", "TPRM-SUP-01"}, "CUSTOMER-MFA": {"TPRM-IAM-01"}}


def main() -> dict:
    case_raw = (BASE / "assessment.json").read_bytes()
    review_raw = (BASE / "control_review.json").read_bytes()
    case = json.loads(case_raw)
    review = json.loads(review_raw)
    canonical_case = json.dumps(case, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    canonical_review = json.dumps(review, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    case_hash = hashlib.sha256(canonical_case).hexdigest()
    review_hash = hashlib.sha256(canonical_review).hexdigest()
    binder = FindingsAssessment.objects.get(ref_id="VAD-SYN-FINDINGS-HPD-2026-001")
    vendor = Entity.objects.get(ref_id="VAD-SYN-VENDOR-001")
    service = Solution.objects.get(ref_id="VAD-SYN-SVC-001")
    ea = EntityAssessment.objects.get(entity=vendor)
    findings = list(Finding.objects.filter(findings_assessment=binder).order_by("ref_id"))
    source_evidence_by_id = {item["evidence_id"]: item for item in case.get("evidence", [])}
    errors = []
    if binder.status != FindingsAssessment.Status.IN_REVIEW:
        errors.append("Findings assessment is no longer in_review")
    if {f.ref_id for f in findings} != {PREFIX + k for k in EXPECTED}:
        errors.append(f"Expected {len(EXPECTED)} scoped findings, got {len(findings)}")
    if not vendor.provided_solutions.filter(ref_id="VAD-SYN-SVC-001").exists():
        errors.append("Expected service is not linked to supplier")
    snapshots = []
    for finding in findings:
        src_id = finding.ref_id.removeprefix(PREFIX)
        if src_id not in EXPECTED:
            errors.append(f"Unexpected managed finding {finding.ref_id}")
            continue
        if finding.status not in (Finding.Status.IDENTIFIED, Finding.Status.CONFIRMED, Finding.Status.ASSIGNED, Finding.Status.IN_PROGRESS):
            errors.append(f"Finding {finding.ref_id} has an unexpected status {finding.status}")
        control_refs = set(finding.applied_controls.values_list("ref_id", flat=True))
        if control_refs != EXPECTED[src_id]:
            errors.append(f"Finding {finding.ref_id} control links differ: {sorted(control_refs)}")
        evidence = list(finding.evidences.all().order_by("name"))
        source = next(x for x in case["findings"] if x["id"] == src_id)
        expected_evidence_ids = {source["evidence_id"], source["retest_evidence_id"]}
        expected_evidence_names = {
            f"VAD synthetic evidence {evidence_id} | {source_evidence_by_id[evidence_id]['label']}"
            for evidence_id in expected_evidence_ids
        }
        actual_evidence_names = {e.name for e in evidence}
        if actual_evidence_names != expected_evidence_names:
            errors.append(f"Finding {finding.ref_id} evidence links differ from source evidence IDs")
        for ev in evidence:
            ev_id = ev.name.split(" | ", 1)[0].removeprefix("VAD synthetic evidence ")
            source_ev = source_evidence_by_id.get(ev_id)
            expected_description = (
                f"Synthetic evidence inventory entry only. {source_ev.get('content_notice', '')} "
                f"Source SHA-256: {case_hash}. No authentic attachment was supplied or verified."
            ) if source_ev else None
            if ev.status != Evidence.Status.MISSING or ev.description != expected_description:
                errors.append(f"Evidence {ev.name} status or source-bound description is incorrect")
        expected_hash_line = f"Source file SHA-256: assessment={case_hash}; control_review={review_hash}"
        if expected_hash_line not in (finding.observation or ""):
            errors.append(f"Finding {finding.ref_id} does not bind to current input hashes")
        snapshots.append({
            "ref_id": finding.ref_id,
            "status": finding.status,
            "severity": finding.severity,
            "control_refs": sorted(control_refs),
            "evidence_names": [e.name for e in evidence],
            "recommendation": finding.recommendation,
            "observation": finding.observation,
        })
    if ea.status != EntityAssessment.Status.IN_REVIEW:
        errors.append("Supplier EntityAssessment is no longer in_review")
    scoped_control_refs = {ref for refs in EXPECTED.values() for ref in refs}
    expected_catalog_refs = {item["id"] for item in review["catalog"]["controls"]}
    managed_controls = list(AppliedControl.objects.filter(ref_id__in=expected_catalog_refs, folder=binder.folder))
    if {c.ref_id for c in managed_controls} != expected_catalog_refs:
        errors.append("The complete 10-control supplier scope is not present in the assessment folder")
    if any(c.status != AppliedControl.Status.TO_DO for c in managed_controls):
        errors.append("One or more of the 10 supplier controls is no longer to_do")
    digest = hashlib.sha256(json.dumps(snapshots, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    result = {
        "case_id": case["case_id"],
        "input_sha256": case.get("input_sha256"),
        "source_file_sha256": {"assessment.json": case_hash, "control_review.json": review_hash},
        "source_hash_format": "canonical-json-v1",
        "vendor_id": case["vendor"]["vendor_id"],
        "service_id": service.ref_id,
        "assessment_id": str(binder.id),
        "link_counts": {
            "vendor": Entity.objects.filter(ref_id=vendor.ref_id).count(),
            "service": vendor.provided_solutions.filter(pk=service.pk).count(),
            "assessment": FindingsAssessment.objects.filter(pk=binder.pk).count(),
            "applied_controls": sum(len(x["control_refs"]) for x in snapshots),
            "unique_applied_controls": len({ref for x in snapshots for ref in x["control_refs"]}),
            "supplier_scope_controls": len(managed_controls),
            "findings": len(findings),
            "evidence": sum(len(x["evidence_names"]) for x in snapshots),
        },
        "verified": not errors,
        "verification_status": "verified" if not errors else "failed",
        "links_verified": not errors,
        "errors": errors,
        "vendor_ref": vendor.ref_id,
        "service_ref": service.ref_id,
        "entity_assessment_status": ea.status,
        "findings_assessment_status": binder.status,
        "findings_count": len(findings),
        "linked_applied_controls": sum(len(x["control_refs"]) for x in snapshots),
        "linked_evidence_records": sum(len(x["evidence_names"]) for x in snapshots),
        "source_sha256": {"assessment.json": case_hash, "control_review.json": review_hash},
        "record_snapshot_sha256": digest,
        "synthetic_only": all(item.get("fictional") is True for item in [case.get("vendor", {})]),
        "approval": "pending",
        "onboarding": "hold",
    }
    if not errors:
        Path("/tmp/platform_sync.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    if errors:
        raise SystemExit(1)
    return result


if __name__ == "__main__":
    main()
