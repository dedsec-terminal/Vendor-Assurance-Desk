"""Sync the synthetic supplier assessment into native CISO Assistant records.

Runs inside the backend container. Inputs are mounted read-only under /input;
no credentials or real supplier data are read by this integration.
"""
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

from django.db import transaction
from core.models import AppliedControl, Evidence, Finding, FindingsAssessment
from iam.models import Folder
from tprm.models import Entity, EntityAssessment, Solution

BASE = Path("/code/db/vad_data")
CASE_REF = "VAD-SYN-VENDOR-001"
ASSESSMENT_REF = "VAD-SYN-FINDINGS-HPD-2026-001"
PREFIX = "VAD-SYN-HPD-"
MAP = {
    "CERT-EXPIRY": ("TPRM-REV-01",),
    "ASSURANCE-SCOPE": ("TPRM-REV-01", "TPRM-SUP-01"),
    "CUSTOMER-MFA": ("TPRM-IAM-01",),
}


def read_json(name: str) -> tuple[dict, str, str]:
    raw = (BASE / name).read_bytes()
    data = json.loads(raw)
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return data, hashlib.sha256(raw).hexdigest(), hashlib.sha256(canonical).hexdigest()


def sync() -> dict:
    case, case_raw_hash, case_hash = read_json("assessment.json")
    review, review_raw_hash, review_hash = read_json("control_review.json")
    evidence_by_id = {item["evidence_id"]: item for item in case.get("evidence", [])}
    if case.get("vendor", {}).get("fictional") is not True:
        raise RuntimeError("Refusing to sync a non-synthetic case")
    if case.get("case_id") != "HPD-2026-001" or case["vendor"].get("vendor_id") != "V-HPD-001" or case["vendor"].get("name") != "HarborPay Demo" or case["vendor"].get("service") != "Payroll processing SaaS":
        raise RuntimeError("Case/vendor/service identity changed; review required before sync")
    if case.get("recommendation", {}).get("status") != "Hold onboarding":
        raise RuntimeError("Source decision changed; review required before sync")
    if {item.get("id") for item in case.get("findings", [])} != set(MAP):
        raise RuntimeError("Finding scope changed; review required before sync")

    with transaction.atomic():
        vendor = Entity.objects.get(ref_id=CASE_REF)
        solution = Solution.objects.get(ref_id="VAD-SYN-SVC-001")
        entity_assessment = EntityAssessment.objects.get(entity=vendor)
        folder = entity_assessment.folder or Folder.get_root_folder()
        control_ids = {c.ref_id: c for c in AppliedControl.objects.filter(ref_id__in={v for vals in MAP.values() for v in vals}, folder=folder)}
        if set(control_ids) != {v for vals in MAP.values() for v in vals}:
            raise RuntimeError("Expected scoped AppliedControl records are missing")

        title = "VAD synthetic supplier findings | HPD-2026-001"
        desc = ("Synthetic finding register linked to HarborPay Demo due diligence. "
                f"Source SHA-256 assessment={case_hash}; control_review={review_hash}. "
                "Training data only; no authentic vendor evidence, approval, or real control result.")
        binder, created = FindingsAssessment.objects.get_or_create(
            ref_id=ASSESSMENT_REF, defaults={
                "name": title, "description": desc,
                "category": FindingsAssessment.Category.SELF_IDENTIFIED,
                "status": FindingsAssessment.Status.IN_REVIEW,
                "version": "1.0", "folder": folder,
                "objectives": "Track synthetic third-party assurance gaps and proposed actions; human review remains pending.",
                "reference_link": "https://github.com/dedsec-terminal/vendor-assurance-desk",
            })
        if not created and (binder.name != title or binder.category != FindingsAssessment.Category.SELF_IDENTIFIED):
            raise RuntimeError("Existing findings assessment conflicts with this integration; refusing overwrite")
        legacy_desc = ("Synthetic finding register linked to HarborPay Demo due diligence. "
                       f"Source SHA-256 assessment={case_raw_hash}; control_review={review_raw_hash}. "
                       "Training data only; no authentic vendor evidence, approval, or real control result.")
        if not created and binder.description != desc:
            if binder.description != legacy_desc:
                raise RuntimeError("Findings Assessment description changed; refusing overwrite")
            binder.description = desc
            binder.save(update_fields=["description"])

        # The source describes baseline issues; retest notes are preserved in each
        # finding, while statuses remain identified until a human closes them.
        counts = {"created": 0, "unchanged": 0}
        for src in case["findings"]:
            ref = PREFIX + src["id"]
            controls = [control_ids[cid] for cid in MAP[src["id"]]]
            obs = (f"Synthetic baseline: {src['baseline_reason']}\n"
                   f"Synthetic retest: {src['retest_reason']}\n"
                   f"Source evidence IDs: {src['evidence_id']}; retest: {src['retest_evidence_id']}\n"
                   f"Source evidence SHA-256: {src['evidence_sha256']}; retest: {src['retest_evidence_sha256']}\n"
                   f"Source file SHA-256: assessment={case_hash}; control_review={review_hash}\n"
                   "All evidence is fictional metadata/mock state, not an authentic artifact.")
            vals = {
                "name": src["title"],
                "description": f"Synthetic third-party risk observation ({src['category']}); no real supplier finding.",
                "folder": folder,
                "findings_assessment": binder,
                "ref_id": ref,
                "priority": None,
                "severity": -1,
                "status": Finding.Status.IDENTIFIED,
                "observation": obs,
                "recommendation": src["required_action"] + " Final disposition requires authorized human review.",
            }
            obj = Finding.objects.filter(ref_id=ref).first()
            if obj:
                legacy_obs = (f"Synthetic baseline: {src['baseline_reason']}\n"
                              f"Synthetic retest: {src['retest_reason']}\n"
                              f"Source evidence IDs: {src['evidence_id']}; retest: {src['retest_evidence_id']}\n"
                              f"Source evidence SHA-256: {src['evidence_sha256']}; retest: {src['retest_evidence_sha256']}\n"
                              f"Source file SHA-256: assessment={case_raw_hash}; control_review={review_raw_hash}\n"
                              "All evidence is fictional metadata/mock state, not an authentic artifact.")
                legacy_migration = all(getattr(obj, k) == v for k, v in vals.items() if k != "observation") and obj.observation == legacy_obs
                if legacy_migration:
                    obj.observation = obs
                    obj.save(update_fields=["observation"])
                expected = {k: (getattr(obj, k) == v) for k, v in vals.items()}
                if not all(expected.values()):
                    raise RuntimeError(f"Managed finding {ref} differs from source/integration state; refusing overwrite")
                if obj.findings_assessment_id != binder.id:
                    raise RuntimeError(f"Managed finding {ref} is attached to a different assessment")
                counts["unchanged"] += 1
            else:
                obj = Finding.objects.create(**vals)
                counts["created"] += 1
            # Relations are also owned by this dedicated VAD finding ref namespace.
            if set(obj.applied_controls.values_list("id", flat=True)) != {c.id for c in controls}:
                if obj.applied_controls.exists():
                    raise RuntimeError(f"Managed finding {ref} has manually changed control links")
                obj.applied_controls.add(*controls)
            evidence_objects = []
            for evidence_id in sorted({src["evidence_id"], src["retest_evidence_id"]}):
                source_evidence = evidence_by_id.get(evidence_id)
                if source_evidence is None:
                    raise RuntimeError(f"Source evidence {evidence_id} is missing")
                ev_name = f"VAD synthetic evidence {evidence_id} | {source_evidence['label']}"
                ev_desc = (f"Synthetic evidence inventory entry only. {source_evidence.get('content_notice', '')} "
                           f"Source SHA-256: {case_hash}. No authentic attachment was supplied or verified.")
                ev, ev_created = Evidence.objects.get_or_create(
                    name=ev_name,
                    folder=folder,
                    defaults={"description": ev_desc, "status": Evidence.Status.MISSING},
                )
                if not ev_created and (ev.description != ev_desc or ev.status != Evidence.Status.MISSING):
                    legacy_ev_desc = (f"Synthetic evidence inventory entry only. {source_evidence.get('content_notice', '')} "
                                      f"Source SHA-256: {case_raw_hash}. No authentic attachment was supplied or verified.")
                    if ev.description != legacy_ev_desc or ev.status != Evidence.Status.MISSING:
                        raise RuntimeError(f"Evidence record {evidence_id} differs from managed synthetic state; refusing overwrite")
                    ev.description = ev_desc
                    ev.save(update_fields=["description"])
                evidence_objects.append(ev)
            if set(obj.evidences.values_list("id", flat=True)) != {e.id for e in evidence_objects}:
                if obj.evidences.exists():
                    raise RuntimeError(f"Managed finding {ref} has manually changed evidence links")
                obj.evidences.add(*evidence_objects)
        return {
            "vendor_ref": vendor.ref_id,
            "service_ref": solution.ref_id,
            "entity_assessment_id": str(entity_assessment.id),
            "findings_assessment_ref": binder.ref_id,
            "findings_assessment_id": str(binder.id),
            "findings_total": binder.findings.count(),
            "findings_created": counts["created"],
            "findings_unchanged": counts["unchanged"],
            "linked_applied_controls": sum(f.applied_controls.count() for f in binder.findings.all()),
            "linked_evidence_records": sum(f.evidences.count() for f in binder.findings.all()),
            "source_sha256": {"assessment.json": case_hash, "control_review.json": review_hash},
            "source_hash_format": "canonical-json-v1",
            "human_approval": "pending",
            "vendor_onboarding": "hold",
            "synthetic_only": True,
        }


if __name__ == "__main__":
    print(json.dumps(sync(), indent=2, sort_keys=True))
