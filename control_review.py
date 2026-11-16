"""Evaluate three IT control populations in the synthetic vendor lab.

The checks adapt the ideas in LedgerCast's test_access_management.py,
test_change_management.py and test_backup_recovery.py. The underlying rows and
review logic here are original fictional training data, not LedgerCast output.
"""
from __future__ import annotations

import csv
from datetime import date, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
AS_OF = date(2026, 11, 16)

CONTROL_SPECS = (
    {
        "id": "ITGC-ACCESS",
        "title": "Vendor workforce access revocation",
        "objective": "Access for terminated vendor personnel is revoked by termination and no later login is recorded.",
        "owner": "Vendor identity and access owner (fictional role)",
        "nist_csf": ["PR.AA-05"],
        "iso_27001": ["A.5.18", "A.8.2"],
        "framework_note": "Related reference points for access rights and privileged access; this lab does not assess full framework conformity.",
    },
    {
        "id": "ITGC-CHANGE",
        "title": "Vendor production change authorization",
        "objective": "Production changes have an accountable approver and approval before deployment.",
        "owner": "Vendor change manager (fictional role)",
        "nist_csf": ["PR.PS-01"],
        "iso_27001": ["A.8.32"],
        "framework_note": "Related reference points for secure configuration and change management. A historical approval after deployment does not cure the sequence failure.",
    },
    {
        "id": "ITGC-BACKUP",
        "title": "Vendor backup completion and restore evidence",
        "objective": "Scheduled backup jobs complete, and the defined restore-test evidence is recorded.",
        "owner": "Vendor service continuity owner (fictional role)",
        "nist_csf": ["PR.DS-11", "RC.RP-03"],
        "iso_27001": ["A.8.13", "A.8.14"],
        "framework_note": "Related reference points for backup, resilience and recovery. A passed fixture check does not prove the vendor's operating effectiveness.",
    },
)
POPULATION_DIRECTORIES = {
    "ITGC-ACCESS": "ITGC-ACCESS",
    "ITGC-CHANGE": "ITGC-CHANGE",
    "ITGC-BACKUP": "ITGC-BACKUP",
}


def _required(row: dict[str, str], field: str) -> str:
    value = row.get(field)
    if value is None or not value.strip():
        raise ValueError(f"required field {field!r} is missing")
    return value.strip()


def _iso_date(row: dict[str, str], field: str) -> date:
    return date.fromisoformat(_required(row, field))


def _date_or_exception(row: dict[str, str], field: str, reasons: list[str]) -> date | None:
    """Parse one date independently so one missing field cannot hide other gaps."""
    try:
        return _iso_date(row, field)
    except (ValueError, TypeError) as exc:
        reasons.append(f"Evidence incomplete or malformed for {field}: {exc}.")
        return None


def _rows(path: Path, required_headers: set[str]) -> list[dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(f"Required training population not found: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or not required_headers.issubset(reader.fieldnames):
            missing = sorted(required_headers - set(reader.fieldnames or []))
            raise ValueError(f"{path.name} is missing required headers: {', '.join(missing)}")
        return list(reader)


def _scope(path: Path, vendor_id: str, vendor_name: str, vendor: dict[str, Any]) -> None:
    if vendor.get("fictional") is not True:
        raise ValueError("ITGC control review accepts only the declared fictional lab vendor.")
    for row in _rows(path, {"vendor_id"}):
        if _required(row, "vendor_id") != vendor_id:
            raise ValueError(f"Vendor scope mismatch in {path.name}; refusing to assess another entity.")
    # Read the population once more below only if the caller independently invokes a check.


def _read_scoped(path: Path, headers: set[str], vendor_id: str, vendor: dict[str, Any]) -> list[dict[str, str]]:
    if vendor.get("fictional") is not True:
        raise ValueError("ITGC control review accepts only the declared fictional lab vendor.")
    rows = _rows(path, headers | {"vendor_id"})
    for row in rows:
        if _required(row, "vendor_id") != vendor_id:
            raise ValueError(f"Vendor scope mismatch in {path.name}; refusing to assess another entity.")
    return rows


def _exception(row: dict[str, str], row_number: int, reasons: list[str]) -> dict[str, Any]:
    return {"record_id": _required(row, "record_id"), "row": row_number,
            "fixture_role": row.get("fixture_role", "population"), "reasons": reasons}


def _check_access(path: Path, vendor_id: str, vendor: dict[str, Any]) -> tuple[int, list[dict[str, Any]], int]:
    rows = _read_scoped(path, {"record_id", "employment_status", "termination_date", "last_login_date", "account_status", "access_removed_date"}, vendor_id, vendor)
    exceptions = []
    tested = 0
    clean = 0
    for row_number, row in enumerate(rows, 2):
        status = _required(row, "employment_status").casefold()
        if status not in ("terminated", "active"):
            reasons = ["Employment status is not recognized; control result is unknown."]
            current_exposure_resolved = False
        elif status == "active":
            # This population only tests termination revocation. Active users are
            # deliberately excluded rather than called compliant by assumption.
            continue
        else:
            tested += 1
            reasons = []
            termination = _date_or_exception(row, "termination_date", reasons)
            last_login = _date_or_exception(row, "last_login_date", reasons)
            removed = _date_or_exception(row, "access_removed_date", reasons)
            try:
                account_status = _required(row, "account_status").casefold()
            except ValueError as exc:
                account_status = "unknown"
                reasons.append(f"Evidence incomplete or malformed: {exc}.")
            if any(value is not None and value > AS_OF for value in (termination, last_login, removed)):
                reasons.append("Evidence date is after the fixed assessment date.")
            if termination and removed and removed > termination:
                reasons.append("Access removal occurred after termination.")
            if termination and last_login and last_login > termination:
                reasons.append("A login is recorded after termination.")
            if account_status != "disabled":
                reasons.append("Account is not recorded as disabled.")
            current_exposure_resolved = bool(
                status == "terminated" and account_status == "disabled"
                and removed is not None and removed <= AS_OF
            )
        if reasons:
            exception = _exception(row, row_number, reasons)
            if status == "terminated":
                exception["current_exposure_resolved"] = current_exposure_resolved
            exceptions.append(exception)
        elif status == "terminated":
            clean += 1
    return tested, exceptions, clean


def _check_change(path: Path, vendor_id: str, vendor: dict[str, Any]) -> tuple[int, list[dict[str, Any]], int]:
    rows = _read_scoped(path, {"record_id", "environment", "approval_date", "deployment_date", "approver"}, vendor_id, vendor)
    exceptions = []
    tested = 0
    clean = 0
    for row_number, row in enumerate(rows, 2):
        environment = _required(row, "environment").casefold()
        if environment not in ("production", "test", "development"):
            reasons = ["Environment is not recognized; control result is unknown."]
        elif environment != "production":
            continue
        else:
            tested += 1
            reasons = []
            try:
                approval = _iso_date(row, "approval_date")
                deployment = _iso_date(row, "deployment_date")
                approver = _required(row, "approver")
                if approval > AS_OF or deployment > AS_OF:
                    reasons.append("Evidence date is after the fixed assessment date.")
                if not approver:
                    reasons.append("Approval lacks an accountable approver.")
                if approval > deployment:
                    reasons.append("Production change was deployed before approval.")
            except (ValueError, TypeError) as exc:
                reasons.append(f"Evidence incomplete or malformed: {exc}.")
        if reasons:
            exceptions.append(_exception(row, row_number, reasons))
        elif environment == "production":
            clean += 1
    return tested, exceptions, clean


def _check_backup(path: Path, vendor_id: str, vendor: dict[str, Any]) -> tuple[int, list[dict[str, Any]], int]:
    rows = _read_scoped(path, {"record_id", "backup_status", "scheduled_date", "completion_date", "restore_test_date", "restore_test_result"}, vendor_id, vendor)
    exceptions = []
    tested = 0
    clean = 0
    for row_number, row in enumerate(rows, 2):
        tested += 1
        reasons = []
        scheduled = _date_or_exception(row, "scheduled_date", reasons)
        completion = _date_or_exception(row, "completion_date", reasons)
        restore_date = _date_or_exception(row, "restore_test_date", reasons)
        try:
            status = _required(row, "backup_status").casefold()
        except ValueError as exc:
            status = "unknown"
            reasons.append(f"Evidence incomplete or malformed: {exc}.")
        try:
            restore_result = _required(row, "restore_test_result").casefold()
        except ValueError as exc:
            restore_result = "unknown"
            reasons.append(f"Evidence incomplete or malformed: {exc}.")
        if any(value is not None and value > AS_OF for value in (scheduled, completion, restore_date)):
            reasons.append("Evidence date is after the fixed assessment date.")
        if status != "success":
            reasons.append(f"Scheduled backup status is {status!r}, not success.")
        if scheduled and completion and completion < scheduled:
            reasons.append("Backup completion predates its scheduled run.")
        if restore_result != "passed":
            reasons.append(f"Restore-test result is {restore_result!r}, not passed.")
        if reasons:
            exceptions.append(_exception(row, row_number, reasons))
        else:
            clean += 1
    return tested, exceptions, clean


def evaluate_controls(root_path: str | Path = ROOT) -> dict[str, Any]:
    """Evaluate baseline and one revised population for HarborPay Demo.

    The case and assessment date are fictional and deterministic. Exceptions
    remain analysis outcomes: this function does not approve or close findings.
    """
    root = Path(root_path).resolve()
    case_path = root / "case-study" / "data.json"
    import json
    case = json.loads(case_path.read_text(encoding="utf-8-sig"))
    if date.fromisoformat(case["assessment_date"]) != AS_OF:
        raise ValueError("This control fixture is bound to the documented 2026-11-16 assessment date.")
    vendor = case["vendors"][0]
    vendor_id = vendor["vendor_id"]
    population_names = {
        "ITGC-ACCESS": ("ITGC-ACCESS", "access_population.csv"),
        "ITGC-CHANGE": ("ITGC-CHANGE", "change_population.csv"),
        "ITGC-BACKUP": ("ITGC-BACKUP", "backup_population.csv"),
    }
    checkers = {"ITGC-ACCESS": _check_access, "ITGC-CHANGE": _check_change, "ITGC-BACKUP": _check_backup}
    controls = []
    clean_flagged = 0
    detected_seeded_ids: set[str] = set()
    clean_flagged = 0
    for spec in CONTROL_SPECS:
        folder_name, filename = population_names[spec["id"]]
        control_dir = root / "case-study" / "itgc" / folder_name
        baseline_path = control_dir / "baseline" / filename
        retest_path = control_dir / "retest" / filename
        checker = checkers[spec["id"]]
        baseline_population, baseline_exceptions, baseline_clean = checker(baseline_path, vendor_id, vendor)
        retest_population, retest_exceptions, _ = checker(retest_path, vendor_id, vendor)
        clean_flagged += sum(e.get("fixture_role") == "clean_comparison" for e in baseline_exceptions)
        # Detection is counted only when the expected seeded record has a
        # finding matching the independent oracle's control-specific signature.
        remaining = len(retest_exceptions)
        status = "gap" if remaining else "pass"
        current_exposure_resolved = (
            all(e.get("current_exposure_resolved") is True for e in retest_exceptions)
            if spec["id"] == "ITGC-ACCESS" and retest_exceptions
            else not retest_exceptions
        )
        controls.append({
            **spec,
            "status": status,
            "current_exposure_resolved": current_exposure_resolved,
            "baseline_population": baseline_population,
            "baseline_exception_count": len(baseline_exceptions),
            "retest_population": retest_population,
            "baseline_exceptions": baseline_exceptions,
            "retest_exceptions": retest_exceptions,
            "baseline_count": len(baseline_exceptions),
            "retest_count": remaining,
            "evidence_paths": [baseline_path.relative_to(root).as_posix(), retest_path.relative_to(root).as_posix()],
            "reason": (
                f"{remaining} exception(s) remain in the retest; an authorized reviewer must assess evidence and remediation."
                if remaining else
                "No exception was detected in the revised synthetic population; this control check is not an approval or effectiveness opinion."
            ),
        })
    expected_path = root / "case-study" / "itgc" / "itgc_expected.json"
    oracle = json.loads(expected_path.read_text(encoding="utf-8-sig"))
    expected_seeded = set(oracle["seeded_failed_controls"])
    expected_signatures = oracle.get("expected_baseline_reason_fragments", {})
    for control in controls:
        control_id = control["id"]
        expected_fragment = expected_signatures.get(control_id)
        if expected_fragment and any(
            e.get("fixture_role") == "seeded_exception"
            and any(expected_fragment in reason for reason in e["reasons"])
            for e in control["baseline_exceptions"]
        ):
            detected_seeded_ids.add(control_id)
    detected_expected = detected_seeded_ids & expected_seeded
    missed_seeded = sorted(expected_seeded - detected_expected)
    unexpected_baseline = sorted(detected_seeded_ids - expected_seeded)
    if not isinstance(oracle.get("expected_clean_exceptions"), int):
        raise ValueError("Independent fixture key must declare expected_clean_exceptions.")
    remaining = sum(c["retest_count"] for c in controls)
    return {
        "assessment_date": AS_OF.isoformat(),
        "vendor_id": vendor_id,
        "vendor_name": vendor["name"],
        "notice": "SYNTHETIC TRAINING DATA. Vendor, personnel, transactions, control evidence and exceptions are fictional; no real supplier was assessed.",
        "scope": "Three sample ITGC populations: terminated-user access, production change approval, backup completion and restore-test evidence.",
        "framework_use": "Proposed related references only. This sample does not measure overall NIST CSF or ISO/IEC 27001 conformity.",
        "human_review": "Pending; no exception is closed and no supplier onboarding decision is made by this runner.",
        "controls": controls,
        "metrics": {
            "seeded_failures_detected": {"actual": len(detected_expected), "expected": len(expected_seeded)},
            "seeded_failures_missed": missed_seeded,
            "unexpected_baseline_controls": unexpected_baseline,
            "clean_rows_flagged_expected": oracle["expected_clean_exceptions"],
            "clean_rows_flagged": clean_flagged,
            "retest_exceptions_remaining": remaining,
            "controls_with_retest_exceptions": sum(c["status"] == "gap" for c in controls),
            "baseline_population_rows": sum(c["baseline_population"] for c in controls),
            "retest_population_rows": sum(c["retest_population"] for c in controls),
            "measurement_scope": "These six small synthetic CSV populations and three selected ITGC checks only.",
        },
    }
