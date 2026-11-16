"""Validate the checked-in native framework readback against its source catalog.

This is an offline consistency check for a recorded snapshot. It does not query
CISO Assistant and must not be described as live platform verification.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "case-study" / "control_catalog.json"
SNAPSHOT_PATH = ROOT / "output" / "framework_links.json"

PRIMARY_REFERENCES = {
    "TPRM-GOV-01": "A.5.19",
    "TPRM-GOV-02": "A.5.19",
    "TPRM-CON-01": "A.5.20",
    "TPRM-SUP-01": "A.5.21",
    "TPRM-IAM-01": "A.5.15",
    "TPRM-CHG-01": "A.8.32",
    "TPRM-OPS-01": "A.8.16",
    "TPRM-IR-01": "A.5.26",
    "TPRM-RES-01": "A.8.13",
    "TPRM-REV-01": "A.5.22",
}


def canonical_json_sha256(value: Any) -> str:
    """Hash canonical JSON so CRLF/LF file endings do not affect the digest."""
    canonical = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def validate(catalog: dict[str, Any], snapshot: dict[str, Any]) -> None:
    """Raise ValueError when the readback does not match the reviewed scope."""
    if snapshot.get("schema") != "vad-native-framework-links-v1":
        raise ValueError("Unexpected framework snapshot schema")
    if snapshot.get("mode") != "verified_readback":
        raise ValueError("Snapshot must be a recorded verified_readback")
    if snapshot.get("catalog_id") != catalog.get("catalog_id"):
        raise ValueError("Snapshot catalog_id does not match the source catalog")
    if snapshot.get("catalog_hash_format") != "canonical-json-v1":
        raise ValueError("Snapshot must use canonical-json-v1 catalog hashing")
    if snapshot.get("catalog_sha256") != canonical_json_sha256(catalog):
        raise ValueError("Snapshot catalog SHA-256 is stale or incorrect")

    controls = catalog.get("controls")
    if not isinstance(controls, list):
        raise ValueError("Catalog controls must be a list")
    control_by_id: dict[str, dict[str, Any]] = {}
    for control in controls:
        question_id = control.get("id")
        if not question_id or question_id in control_by_id:
            raise ValueError("Catalog question IDs must be nonempty and unique")
        control_by_id[question_id] = control
    if set(control_by_id) != set(PRIMARY_REFERENCES):
        raise ValueError("Catalog question IDs differ from the reviewed ten-control scope")

    library = snapshot.get("source_library") or {}
    if (library.get("ref_id") != "ISO/IEC 27001:2022"
            or library.get("version") != "19"
            or library.get("native_record_count") != 93):
        raise ValueError("Snapshot does not identify the expected ISO/IEC 27001:2022 library")

    links = snapshot.get("links")
    if not isinstance(links, list):
        raise ValueError("Snapshot links must be a list")
    link_by_id: dict[str, dict[str, Any]] = {}
    for link in links:
        question_id = link.get("question_id")
        if not question_id or question_id in link_by_id:
            raise ValueError("Snapshot question IDs must be nonempty and unique")
        link_by_id[question_id] = link
    if len(links) != len(PRIMARY_REFERENCES) or set(link_by_id) != set(PRIMARY_REFERENCES):
        raise ValueError("Snapshot must contain exactly the ten reviewed question links")
    if snapshot.get("linked_question_count") != 10:
        raise ValueError("linked_question_count must be ten")

    native_ids_by_ref: dict[str, str] = {}
    refs_by_native_id: dict[str, str] = {}
    for question_id, expected_ref in PRIMARY_REFERENCES.items():
        link = link_by_id[question_id]
        source_refs = control_by_id[question_id].get("iso_27001", [])
        if expected_ref not in source_refs:
            raise ValueError(f"Expected primary {expected_ref} is absent from {question_id} source crosswalk")
        if link.get("native_ref_id") != expected_ref:
            raise ValueError(f"Native ISO reference mismatch for {question_id}")
        native_record_id = link.get("native_record_id")
        if not isinstance(native_record_id, str) or not native_record_id.strip():
            raise ValueError(f"Missing native record ID for {question_id}")
        prior_id = native_ids_by_ref.setdefault(expected_ref, native_record_id)
        if prior_id != native_record_id:
            raise ValueError(f"The same native reference {expected_ref} has inconsistent record IDs")
        prior_ref = refs_by_native_id.setdefault(native_record_id, expected_ref)
        if prior_ref != expected_ref:
            raise ValueError(f"Different native references share record ID {native_record_id}")
        if link.get("status") != "to_do":
            raise ValueError(f"Control {question_id} is not still to_do")

    if (snapshot.get("unique_native_reference_count") != 9
            or len(native_ids_by_ref) != 9 or len(refs_by_native_id) != 9):
        raise ValueError("Snapshot must map to nine distinct native ISO references")
    if snapshot.get("assessment_status") != "in_review":
        raise ValueError("Supplier assessment must remain in_review")
    if snapshot.get("findings_assessment_status") != "in_review":
        raise ValueError("Findings assessment must remain in_review")
    if snapshot.get("assessment_and_finding_states_unchanged") is not True:
        raise ValueError("Snapshot must confirm assessment and finding state preservation")
    if snapshot.get("finding_count") != 3:
        raise ValueError("Snapshot must retain the three seeded findings")
    if snapshot.get("finding_status_counts") != {"identified": 3}:
        raise ValueError("All three seeded findings must remain identified")
    if snapshot.get("all_scoped_controls_remain_to_do") is not True:
        raise ValueError("Snapshot must confirm all scoped controls remain to_do")


def main() -> None:
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    validate(catalog, snapshot)
    print("Framework snapshot is internally consistent (recorded readback; offline check).")


if __name__ == "__main__":
    main()
