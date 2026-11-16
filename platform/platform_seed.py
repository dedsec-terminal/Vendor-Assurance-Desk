"""Seed an idempotent synthetic TPRM demonstration into local CISO Assistant."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import django

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "platform" / "ciso-assistant" / "backend"
sys.path.insert(0, str(BACKEND))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ciso_assistant.settings")
django.setup()

from django.db import transaction  # noqa: E402
from core.models import AppliedControl, StoredLibrary  # noqa: E402
from iam.models import Folder  # noqa: E402
from tprm.models import Entity, EntityAssessment, Tier  # noqa: E402
from tprm.tiers import set_entity_tier  # noqa: E402


@transaction.atomic
def seed() -> dict:
    catalog = json.loads((ROOT / "case-study" / "control_catalog.json").read_text("utf-8"))
    case = json.loads((ROOT / "case-study" / "data.json").read_text("utf-8"))
    vendor = case["vendors"][0]
    root_folder = Folder.get_root_folder()
    entity, created = Entity.objects.update_or_create(
        ref_id="VAD-SYN-VENDOR-001",
        defaults={
            "name": vendor["name"],
            "description": (
                "Fictional payroll SaaS supplier used for a TPRM learning case. "
                "All records and evidence references are synthetic."
            ),
            "country": "IND",
            "mission": "Processes fictional employee payroll, identity and bank details.",
            "folder": root_folder,
        },
    )
    tier, _ = Tier.objects.get_or_create(
        key="vad-important",
        defaults={"name": "VAD Important", "rank": Tier.next_rank(), "hexcolor": "#555555"},
    )
    if entity.tier_id != tier.id:
        set_entity_tier(
            entity,
            tier,
            note="Synthetic case-study tier based on fictional service criticality; not a real supplier decision.",
        )
    solution, _ = entity.provided_solutions.update_or_create(
        ref_id="VAD-SYN-SVC-001",
        defaults={
            "name": vendor["service"],
            "description": "Fictional payroll service; synthetic employee records only.",
            "tier": tier,
            "storage_of_data": True,
            "data_location_storage": "IND",
            "data_location_processing": "IND",
        },
    )
    assessment, assessment_created = EntityAssessment.objects.get_or_create(
        name="VAD synthetic supplier due diligence 2026-11",
        entity=entity,
        defaults={
            "description": (
                "Demonstration assessment using the Vendor Assurance Desk's "
                f"{len(catalog['controls'])}-question control catalog ({catalog['catalog_id']}). "
                "Framework references are proposed mappings, not a compliance opinion."
            ),
            "status": EntityAssessment.Status.IN_REVIEW,
            "version": "1.0",
            "folder": root_folder,
            "observation": (
                "Evidence review is simulated using fictional evidence references. "
                "No real supplier documents were supplied or verified."
            ),
        },
    )
    assessment.solutions.add(solution)
    for control in catalog["controls"]:
        refs = (
            f"NIST CSF 2.0: {', '.join(control['nist_csf'])}; "
            f"ISO/IEC 27001:2022: {', '.join(control['iso_27001'])}"
        )
        description = (
            f"Vendor: {entity.name}\nAssessment: {assessment.name}\n"
            f"Reviewer question: {control['question']}\n"
            f"Objective: {control['objective']}\n"
            f"Evidence to request: {', '.join(control['expected_evidence'])}\n"
            f"Proposed references: {refs}\n"
            f"Mapping rationale: {control['mapping_rationale']}\n"
            "Reference matches support scoping only; they do not establish compliance or formal equivalence."
        )
        AppliedControl.objects.update_or_create(
            ref_id=control["id"],
            folder=root_folder,
            defaults={
                "name": f"{control['id']} | {control['title']}",
                "description": description,
                "status": AppliedControl.Status.TO_DO,
            },
        )
    return {
        "entity_created": created,
        "assessment_created": assessment_created,
        "entity_count": Entity.objects.filter(ref_id="VAD-SYN-VENDOR-001").count(),
        "solution_count": entity.provided_solutions.filter(ref_id="VAD-SYN-SVC-001").count(),
        "assessment_count": EntityAssessment.objects.filter(entity=entity).count(),
        "applied_control_count": AppliedControl.objects.filter(
            ref_id__startswith="TPRM-", folder=root_folder
        ).count(),
        "catalog_control_count": len(catalog["controls"]),
        "vendor_ref": entity.ref_id,
        "assessment_name": assessment.name,
        "assessment_status": assessment.status,
        "tier": entity.tier.key,
        "nist_csf_library_loaded": StoredLibrary.objects.filter(
            name__icontains="NIST CSF 2.0"
        ).exists(),
        "iso_27001_library_loaded": StoredLibrary.objects.filter(
            name__icontains="ISO/IEC 27001:2022"
        ).exists(),
    }


if __name__ == "__main__":
    print(json.dumps(seed(), indent=2))
