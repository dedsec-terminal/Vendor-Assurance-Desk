"""Idempotently seed the synthetic HarborPay TPRM case into Docker CISO Assistant.

This file is staged in a private Docker data volume and run in the backend container.
It reads only the synthetic case and original 10-question catalog from that volume.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, "/code")
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ciso_assistant.settings")
django.setup()

from django.db import transaction
from core.models import AppliedControl, StoredLibrary
from iam.models import Folder
from tprm.models import Entity, EntityAssessment, Tier
from tprm.tiers import set_entity_tier


@transaction.atomic
def seed() -> dict:
    base = Path("/code/db/vad_data")
    catalog = json.loads((base / "control_catalog.json").read_text("utf-8"))
    case = json.loads((base / "data.json").read_text("utf-8"))
    vendor = case["vendors"][0]
    root_folder = Folder.get_root_folder()
    entity, created = Entity.objects.update_or_create(
        ref_id="VAD-SYN-VENDOR-001",
        defaults={
            "name": vendor["name"],
            "description": "Fictional HarborPay Demo payroll SaaS supplier for a TPRM training case. All evidence and records are synthetic.",
            "country": "IND",
            "mission": "Processes synthetic employee identity, payroll and bank account details.",
            "folder": root_folder,
        },
    )
    tier, _ = Tier.objects.get_or_create(
        key="vad-proposed-high",
        defaults={"name": "Proposed High (lab)", "rank": Tier.next_rank(), "hexcolor": "#555555"},
    )
    if entity.tier_id != tier.id:
        set_entity_tier(entity, tier, note="Proposed training-case tier from fictional service criticality; reviewer confirmation required, not a real supplier decision.")
    solution, _ = entity.provided_solutions.update_or_create(
        ref_id="VAD-SYN-SVC-001",
        defaults={
            "name": vendor["service"],
            "description": "Fictional payroll processing SaaS; synthetic employee information only.",
            "tier": tier,
            "storage_of_data": True,
            "data_location_storage": "IND",
            "data_location_processing": "IND",
        },
    )
    assessment, assessment_created = EntityAssessment.objects.get_or_create(
        name="VAD HarborPay synthetic supplier due diligence 2026-11",
        entity=entity,
        defaults={
            "description": f"Synthetic evidence review using the {len(catalog['controls'])}-question catalog ({catalog['catalog_id']}); proposed NIST CSF 2.0 and ISO/IEC 27001:2022 mappings are scoping references, not a compliance opinion.",
            "status": EntityAssessment.Status.IN_REVIEW,
            "version": "1.0",
            "folder": root_folder,
            "observation": "Training case only. All supplier, service and evidence records are fictional; no real supplier documents were supplied or verified.",
        },
    )
    assessment.solutions.add(solution)
    for control in catalog["controls"]:
        refs = f"NIST CSF 2.0: {', '.join(control['nist_csf'])}; ISO/IEC 27001:2022: {', '.join(control['iso_27001'])}"
        description = (
            f"Vendor: {entity.name}\nAssessment: {assessment.name}\n"
            f"Reviewer question: {control['question']}\nObjective: {control['objective']}\n"
            f"Evidence to request: {', '.join(control['expected_evidence'])}\n"
            f"Proposed references: {refs}\nMapping rationale: {control['mapping_rationale']}\n"
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
        "vendor_count": Entity.objects.filter(ref_id="VAD-SYN-VENDOR-001").count(),
        "solution_count": entity.provided_solutions.filter(ref_id="VAD-SYN-SVC-001").count(),
        "assessment_count": EntityAssessment.objects.filter(entity=entity).count(),
        "applied_control_count": AppliedControl.objects.filter(ref_id__startswith="TPRM-", folder=root_folder).count(),
        "catalog_control_count": len(catalog["controls"]),
        "vendor_ref": entity.ref_id,
        "vendor_name": entity.name,
        "service_name": solution.name,
        "assessment_name": assessment.name,
        "assessment_status": assessment.status,
        "tier": entity.tier.name,
        "nist_csf_library_loaded": StoredLibrary.objects.filter(name__icontains="NIST CSF 2.0").exists(),
        "iso_27001_library_loaded": StoredLibrary.objects.filter(name__icontains="ISO/IEC 27001:2022").exists(),
    }


if __name__ == "__main__":
    print(json.dumps(seed(), indent=2))
