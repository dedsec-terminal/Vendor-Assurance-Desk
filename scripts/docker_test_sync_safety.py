"""Bounded regression checks for idempotence, drift guards, and evidence links.

Run inside the backend after staging the same inputs as docker_sync_assessment.py.
All deliberate database mutations are enclosed in transactions rolled back here.
"""
from __future__ import annotations
import json
import shutil
import io
import tempfile
from pathlib import Path
from contextlib import redirect_stdout

import docker_sync_assessment as sync_module
import docker_verify_sync as verify_module
from django.db import transaction
from core.models import Evidence, Finding


class ExpectedRollback(Exception):
    pass


def main() -> dict:
    first = sync_module.sync()
    second = sync_module.sync()
    assert first["findings_total"] == second["findings_total"] == 3
    assert second["findings_created"] == 0 and second["findings_unchanged"] == 3

    original_base = sync_module.BASE
    with tempfile.TemporaryDirectory(prefix="vad-source-drift-") as tmp:
        test_base = Path(tmp)
        for name in ("assessment.json", "control_review.json"):
            shutil.copyfile(original_base / name, test_base / name)
        case_path = test_base / "assessment.json"
        changed = json.loads(case_path.read_text("utf-8"))
        changed["vendor"]["name"] += " changed"
        case_path.write_text(json.dumps(changed), encoding="utf-8")
        sync_module.BASE = test_base
        try:
            try:
                sync_module.sync()
                raise AssertionError("Changed source identity was accepted")
            except RuntimeError as exc:
                assert "identity changed" in str(exc)
        finally:
            sync_module.BASE = original_base

    # A same-count swap to another synthetic Evidence row must fail exact-link
    # verification; the transaction restores the original relation afterward.
    try:
        with transaction.atomic():
            finding = Finding.objects.get(ref_id="VAD-SYN-HPD-CERT-EXPIRY")
            swapped = Evidence.objects.get(name__startswith="VAD synthetic evidence E02 |")
            finding.evidences.clear()
            finding.evidences.add(swapped)
            try:
                with redirect_stdout(io.StringIO()):
                    verify_module.main()
                raise AssertionError("Swapped evidence link was accepted")
            except SystemExit as exc:
                assert exc.code == 1
            raise ExpectedRollback()
    except ExpectedRollback:
        pass

    # A human status edit is detected and remains untouched by the sync attempt.
    try:
        with transaction.atomic():
            finding = Finding.objects.get(ref_id="VAD-SYN-HPD-CERT-EXPIRY")
            finding.status = Finding.Status.IN_PROGRESS
            finding.save(update_fields=["status"])
            try:
                sync_module.sync()
                raise AssertionError("Managed-record drift was overwritten")
            except RuntimeError as exc:
                assert "differs from source" in str(exc)
            finding.refresh_from_db()
            assert finding.status == Finding.Status.IN_PROGRESS
            raise ExpectedRollback()
    except ExpectedRollback:
        pass

    final = verify_module.main()
    assert final["verified"] and final["link_counts"]["findings"] == 3
    return {"idempotent_second_run": True, "source_change_rejected": True,
            "same_count_evidence_swap_rejected_and_rolled_back": True,
            "manual_status_change_preserved_and_test_rolled_back": True,
            "final_readback_verified": True,
            "record_snapshot_sha256": final["record_snapshot_sha256"]}


if __name__ == "__main__":
    print(json.dumps(main(), indent=2, sort_keys=True))
