"""Link VAD's ten scoped controls to one exact native ISO 27001:2022 control each.

Default is a no-write dry run. Use --apply only after reviewing the printed plan.
The CISO Assistant model has one nullable ReferenceControl FK per AppliedControl;
NIST crosswalk IDs therefore remain proposed source references, not extra links.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, "/code")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ciso_assistant.settings")
import django
django.setup()

from django.db import transaction
from core.models import AppliedControl, FindingsAssessment, Finding, ReferenceControl, StoredLibrary
from iam.models import Folder
from tprm.models import Entity, EntityAssessment

DATA = Path("/code/db/vad_data")
CATALOG = DATA / "control_catalog.json"
OUT = Path("/code/db/framework_links.json")
CASE_REF = "VAD-SYN-VENDOR-001"
FINDINGS_REF = "VAD-SYN-FINDINGS-HPD-2026-001"
LIBRARY_REF = "ISO/IEC 27001:2022"
LIBRARY_NAME = "International standard ISO/IEC 27001:2022"
LIBRARY_VERSION = "19"

# One primary Annex A association per question because the native product model
# exposes a single FK, not a many-to-many control mapping.
PRIMARY = {
    "TPRM-GOV-01": ("A.5.19", "Supplier relationships is the closest primary topic to pre-engagement supplier diligence."),
    "TPRM-GOV-02": ("A.5.19", "Supplier relationship governance is the closest primary topic to lifecycle ownership."),
    "TPRM-CON-01": ("A.5.20", "Supplier agreements directly cover the security obligations in contracts."),
    "TPRM-SUP-01": ("A.5.21", "ICT supply-chain security directly covers downstream service dependencies."),
    "TPRM-IAM-01": ("A.5.15", "Access control is the broad primary topic; identity, access-rights and authentication references remain proposed crosswalks."),
    "TPRM-CHG-01": ("A.8.32", "Change management directly covers authorization, testing and release of service changes."),
    "TPRM-OPS-01": ("A.8.16", "Monitoring activities is the closest primary topic to reviewing security-relevant activity."),
    "TPRM-IR-01": ("A.5.26", "Incident response directly covers coordinated response to service-impacting incidents."),
    "TPRM-RES-01": ("A.8.13", "Information backup is the closest primary topic to service backup and restore evidence."),
    "TPRM-REV-01": ("A.5.22", "Supplier service monitoring and review is the closest primary topic to reassessment and follow-up."),
}


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical_json_sha256(data: dict) -> str:
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return sha256(canonical)


def exactly_one(matches: list, label: str):
    if len(matches) != 1:
        raise RuntimeError(f"{label} is missing or ambiguous (matches={len(matches)})")
    return matches[0]


def validate_exact_unique_ids(actual_ids: list[str], expected_ids: set[str], label: str) -> None:
    if len(actual_ids) != len(set(actual_ids)):
        raise RuntimeError(f"{label} contains duplicate identifiers")
    if len(actual_ids) != len(expected_ids) or set(actual_ids) != expected_ids:
        raise RuntimeError(f"{label} differs from the expected ten-item scope")


def ensure_reference_compatible(existing_id, expected_id, label: str) -> None:
    if existing_id is not None and str(existing_id) != str(expected_id):
        raise RuntimeError(f"{label} has a conflicting native reference")


def validate_reference_map(rows: list[tuple[str, str | None]], expected: dict[str, str], label: str) -> None:
    validate_exact_unique_ids([question_id for question_id, _ in rows], set(expected), label)
    for question_id, reference_id in rows:
        ensure_reference_compatible(reference_id, expected[question_id], f"{label} {question_id}")
        if reference_id is None:
            raise RuntimeError(f"{label} {question_id} is missing its expected native reference")


def guard_self_test() -> dict:
    rejected = {}
    for name, candidates in (("unknown_id", []), ("ambiguous_match", [object(), object()])):
        try:
            exactly_one(candidates, name)
        except RuntimeError:
            rejected[name] = True
        else:
            raise RuntimeError(f"Fail-closed selection test did not reject {name}")
    cases = (
        ("duplicate_catalog_ids", lambda: validate_exact_unique_ids(["Q1", "Q1"], {"Q1"}, "catalog")),
        ("duplicate_applied_control_ids", lambda: validate_exact_unique_ids(["Q1", "Q1"], {"Q1"}, "controls")),
        ("conflicting_reference_id", lambda: ensure_reference_compatible("unexpected", "expected", "control")),
        ("wrong_locked_fk_readback", lambda: validate_reference_map([("Q1", "wrong")], {"Q1": "expected"}, "locked controls")),
    )
    for name, check in cases:
        try:
            check()
        except RuntimeError:
            rejected[name] = True
        else:
            raise RuntimeError(f"Fail-closed association test did not reject {name}")
    return rejected


def resolve_scope() -> tuple[dict, Folder, list[AppliedControl], StoredLibrary, dict[str, ReferenceControl]]:
    catalog_raw = CATALOG.read_bytes()
    catalog = json.loads(catalog_raw)
    source_control_rows = catalog.get("controls", [])
    validate_exact_unique_ids([item["id"] for item in source_control_rows], set(PRIMARY), "Catalog controls")
    source_controls = {item["id"]: item for item in source_control_rows}
    for control_id, (ref_id, _) in PRIMARY.items():
        item = source_controls[control_id]
        if ref_id not in item.get("iso_27001", []):
            raise RuntimeError(f"Chosen native reference {ref_id} is absent from {control_id}'s source crosswalk")

    vendor = Entity.objects.get(ref_id=CASE_REF)
    assessment = EntityAssessment.objects.get(entity=vendor)
    folder = assessment.folder or Folder.get_root_folder()
    controls = list(AppliedControl.objects.filter(folder=folder, ref_id__in=PRIMARY).order_by("ref_id"))
    validate_exact_unique_ids([item.ref_id for item in controls], set(PRIMARY), "Scoped AppliedControl records")
    if any(item.status != AppliedControl.Status.TO_DO for item in controls):
        raise RuntimeError("A scoped AppliedControl status changed; refusing mapping")
    finding_assessment = FindingsAssessment.objects.get(ref_id=FINDINGS_REF)
    findings = list(Finding.objects.filter(findings_assessment=finding_assessment).order_by("ref_id"))

    libraries = list(StoredLibrary.objects.filter(ref_id=LIBRARY_REF))
    library = exactly_one(libraries, f"stored {LIBRARY_REF} source library")
    if library.name != LIBRARY_NAME or str(library.version) != LIBRARY_VERSION:
        raise RuntimeError("Stored ISO library title or version changed; inspect before mapping")
    refs_in_source = {row.get("ref_id"): row for row in library.content.get("reference_controls", [])}
    resolved = {}
    for control_id, (ref_id, _) in PRIMARY.items():
        source_matches = [row for row in library.content.get("reference_controls", []) if row.get("ref_id") == ref_id]
        native_matches = list(ReferenceControl.objects.filter(ref_id=ref_id, library__ref_id=LIBRARY_REF))
        exactly_one(source_matches, f"source library reference {ref_id}")
        if library.is_loaded:
            resolved[control_id] = exactly_one(native_matches, f"loaded native reference {ref_id}")
        else:
            if ref_id not in refs_in_source:
                raise RuntimeError(f"Reference {ref_id} is absent from stored ISO source library")
    return catalog, folder, controls, library, resolved


def state_snapshot(folder: Folder, controls: list[AppliedControl], findings: list[Finding], binder: FindingsAssessment) -> dict:
    return {
        "assessment_status": EntityAssessment.objects.get(entity__ref_id=CASE_REF).status,
        "findings_assessment_status": binder.status,
        "controls": [(item.ref_id, item.status, str(item.folder_id)) for item in controls],
        "findings": [(item.ref_id, item.status, item.severity) for item in findings],
    }


def execute(apply: bool) -> dict:
    guard_checks = guard_self_test()
    catalog_raw = CATALOG.read_bytes()
    catalog, folder, controls, library, resolved = resolve_scope()
    binder = FindingsAssessment.objects.get(ref_id=FINDINGS_REF)
    findings = list(Finding.objects.filter(findings_assessment=binder).order_by("ref_id"))
    before = state_snapshot(folder, controls, findings, binder)

    imported = False
    plan = []
    if apply:
        # Import and FK changes share one DB transaction. A failure rolls both back.
        with transaction.atomic():
            if not library.is_loaded:
                msg = library.load()
                if msg:
                    raise RuntimeError(f"CISO Assistant ISO library import failed: {msg}")
                imported = True
            resolved = {}
            for control_id, (ref_id, _) in PRIMARY.items():
                matches = list(ReferenceControl.objects.filter(ref_id=ref_id, library__ref_id=LIBRARY_REF))
                resolved[control_id] = exactly_one(matches, f"native reference {ref_id}")
            for item in controls:
                ensure_reference_compatible(item.reference_control_id, resolved[item.ref_id].id, item.ref_id)
            for item in controls:
                ref_id, rationale = PRIMARY[item.ref_id]
                target = resolved[item.ref_id]
                plan.append({"question_id": item.ref_id, "native_ref_id": ref_id,
                             "native_record_id": str(target.id),
                             "action": "unchanged" if item.reference_control_id else "link",
                             "rationale": rationale})
            current = list(AppliedControl.objects.select_for_update().filter(folder=folder, ref_id__in=PRIMARY).order_by("ref_id"))
            validate_exact_unique_ids([item.ref_id for item in current], set(PRIMARY), "Locked AppliedControl records")
            if [(x.ref_id, x.status, str(x.folder_id)) for x in current] != before["controls"]:
                raise RuntimeError("Scoped controls changed after plan; refusing mutation")
            for item in current:
                target = resolved[item.ref_id]
                ensure_reference_compatible(item.reference_control_id, target.id, item.ref_id)
                if not item.reference_control_id:
                    item.reference_control = target
                    item.save(update_fields=["reference_control"])
            transaction_controls = list(AppliedControl.objects.select_related("reference_control").filter(folder=folder, ref_id__in=PRIMARY).order_by("ref_id"))
            validate_exact_unique_ids([item.ref_id for item in transaction_controls], set(PRIMARY), "Transaction readback controls")
            validate_reference_map([(item.ref_id, str(item.reference_control_id) if item.reference_control_id else None) for item in transaction_controls],
                                   {question_id: str(resolved[question_id].id) for question_id in PRIMARY},
                                   "Transaction readback")
            transaction_findings = list(Finding.objects.filter(findings_assessment=binder).order_by("ref_id"))
            if before != state_snapshot(folder, transaction_controls, transaction_findings, binder):
                raise RuntimeError("Mapping changed assessment/finding state; rolling back transaction")
        controls = list(AppliedControl.objects.filter(folder=folder, ref_id__in=PRIMARY).order_by("ref_id"))
        findings = list(Finding.objects.filter(findings_assessment=binder).order_by("ref_id"))
        after = state_snapshot(folder, controls, findings, binder)
        if before != after:
            raise RuntimeError("Mapping changed assessment/finding status or scope")
    else:
        for item in controls:
            ref_id, rationale = PRIMARY[item.ref_id]
            if item.reference_control_id:
                raise RuntimeError(f"{item.ref_id} already has a native association; rerun verifier before planning")
            plan.append({"question_id": item.ref_id, "native_ref_id": ref_id,
                         "native_record_id": None, "action": "dry_run_link", "rationale": rationale})

    payload = {
        "schema": "vad-native-framework-links-v1",
        "mode": "applied" if apply else "dry_run",
        "catalog_id": catalog.get("catalog_id"),
        "catalog_sha256": canonical_json_sha256(catalog),
        "catalog_hash_format": "canonical-json-v1",
        "platform": "CISO Assistant v4.3.2",
        "native_model": "core.AppliedControl.reference_control -> core.ReferenceControl",
        "association_cardinality": "one ReferenceControl per AppliedControl",
        "source_library": {"ref_id": LIBRARY_REF, "name": LIBRARY_NAME, "version": LIBRARY_VERSION,
                           "loaded_by_run": imported},
        "linked_question_count": len(plan),
        "unique_native_reference_count": len({item["native_ref_id"] for item in plan}),
        "fail_closed_guard_checks": guard_checks,
        "links": plan,
        "assessment_and_finding_states_unchanged": (before == state_snapshot(folder, controls, findings, binder)) if apply else None,
        "interpretation": "Primary topical associations only; not compliance evidence, equivalence, or certification.",
        "limitations": ["The native relationship is single-valued, so additional NIST and ISO crosswalks remain proposed in the source catalog.",
                        "NIST CSF 2.0 native ReferenceControl records were not available in this local database; no NIST FK was created."],
    }
    if apply:
        OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="import the exact bundled ISO library if needed and set native references")
    args = parser.parse_args()
    print(json.dumps(execute(args.apply), indent=2, sort_keys=True))
