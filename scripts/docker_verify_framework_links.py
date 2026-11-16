"""Read-only Django ORM verification of VAD's native framework links."""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, "/code")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ciso_assistant.settings")
import django
django.setup()

from core.models import AppliedControl, FindingsAssessment, Finding, ReferenceControl, StoredLibrary
from iam.models import Folder
from tprm.models import Entity, EntityAssessment
from docker_link_frameworks import CASE_REF, FINDINGS_REF, LIBRARY_NAME, LIBRARY_REF, LIBRARY_VERSION, OUT, PRIMARY, CATALOG, guard_self_test, canonical_json_sha256, validate_exact_unique_ids, validate_reference_map


def verify() -> dict:
    if not CATALOG.exists() or not OUT.exists():
        raise RuntimeError("Expected catalog and applied mapping proof are missing")
    catalog_raw = CATALOG.read_bytes()
    catalog = json.loads(catalog_raw)
    stored = json.loads(OUT.read_text(encoding="utf-8"))
    raw_catalog_hash = hashlib.sha256(catalog_raw).hexdigest()
    catalog_hash = canonical_json_sha256(catalog)
    stored_format = stored.get("catalog_hash_format")
    if stored_format == "canonical-json-v1":
        hash_matches = stored.get("catalog_sha256") == catalog_hash
    elif stored_format in (None, "sha256-raw-bytes-v1"):
        # One-time migration for prior proof files: accept raw bytes only when
        # they match this exact checked-out catalog, then write canonical below.
        hash_matches = stored.get("catalog_sha256") == raw_catalog_hash
    else:
        hash_matches = False
    if stored.get("mode") not in ("applied", "verified_readback") or not hash_matches:
        raise RuntimeError("Applied proof does not match current control catalog")
    library = StoredLibrary.objects.get(ref_id=LIBRARY_REF)
    if library.name != LIBRARY_NAME or str(library.version) != LIBRARY_VERSION or not library.is_loaded:
        raise RuntimeError("Exact ISO/IEC 27001:2022 source library is not loaded")
    vendor = Entity.objects.get(ref_id=CASE_REF)
    assessment = EntityAssessment.objects.get(entity=vendor)
    folder = assessment.folder or Folder.get_root_folder()
    controls = list(AppliedControl.objects.filter(folder=folder, ref_id__in=PRIMARY).select_related("reference_control", "reference_control__library").order_by("ref_id"))
    validate_exact_unique_ids([row.ref_id for row in controls], set(PRIMARY), "Verified AppliedControl records")
    links = []
    expected_fk_by_question = {}
    for item in controls:
        expected, rationale = PRIMARY[item.ref_id]
        ref = item.reference_control
        if item.status != AppliedControl.Status.TO_DO:
            raise RuntimeError(f"{item.ref_id} status changed")
        if ref is None or ref.ref_id != expected or ref.library.ref_id != LIBRARY_REF:
            raise RuntimeError(f"{item.ref_id} native FK does not point to exact expected library control")
        matches = ReferenceControl.objects.filter(ref_id=expected, library__ref_id=LIBRARY_REF).count()
        if matches != 1:
            raise RuntimeError(f"Native control {expected} is ambiguous in the selected library")
        expected_fk_by_question[item.ref_id] = str(ref.id)
        links.append({"question_id": item.ref_id, "native_ref_id": ref.ref_id,
                      "native_record_id": str(ref.id), "status": item.status})
    validate_reference_map([(item.ref_id, str(item.reference_control_id) if item.reference_control_id else None) for item in controls],
                           expected_fk_by_question,
                           "Verified controls")

    binder = FindingsAssessment.objects.get(ref_id=FINDINGS_REF)
    findings = list(Finding.objects.filter(findings_assessment=binder).order_by("ref_id"))
    if assessment.status != EntityAssessment.Status.IN_REVIEW or binder.status != FindingsAssessment.Status.IN_REVIEW:
        raise RuntimeError("Supplier or findings assessment moved out of review")
    if len(findings) != 3 or any(item.status != Finding.Status.IDENTIFIED for item in findings):
        raise RuntimeError("Existing finding records or states changed")
    if stored.get("assessment_and_finding_states_unchanged") is not True:
        raise RuntimeError("Apply run did not confirm review/finding state preservation")

    proof = {
        "schema": "vad-native-framework-links-v1",
        "mode": "verified_readback",
        "platform": stored["platform"],
        "catalog_id": catalog["catalog_id"],
        "catalog_sha256": catalog_hash,
        "catalog_hash_format": "canonical-json-v1",
        "source_library": {"ref_id": library.ref_id, "name": library.name, "version": str(library.version), "native_record_count": ReferenceControl.objects.filter(library__ref_id=LIBRARY_REF).count()},
        "linked_question_count": len(links),
        "unique_native_reference_count": len({link["native_ref_id"] for link in links}),
        "fail_closed_guard_checks": guard_self_test(),
        "links": links,
        "assessment_status": assessment.status,
        "findings_assessment_status": binder.status,
        "assessment_and_finding_states_unchanged": True,
        "finding_count": len(findings),
        "finding_status_counts": {status: sum(1 for item in findings if item.status == status) for status in sorted({item.status for item in findings})},
        "all_scoped_controls_remain_to_do": all(item.status == AppliedControl.Status.TO_DO for item in controls),
        "interpretation": "Primary topical associations only; not compliance evidence, equivalence, or certification.",
        "limitations": stored["limitations"],
    }
    OUT.write_text(json.dumps(proof, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return proof


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2, sort_keys=True))
