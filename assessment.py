"""Repeatable, evidence-linked vendor review. Standard library only."""
from __future__ import annotations

import argparse
import csv
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CHECK_VERSION = "1.1.0"
SCOPE = "Synthetic training case; selected metadata checks only. Human approval required."
CHECKS = (
    ("CERT-EXPIRY", "E01", "Assurance freshness"),
    ("ASSURANCE-SCOPE", "E02", "Assurance scope"),
    ("CUSTOMER-MFA", "E03", "Customer responsibility"),
    ("POLICY-CHECK", "E04", "Access policy"),
)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_json(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def validate_case(case):
    date.fromisoformat(case["assessment_date"])
    if not case.get("vendors") or not case.get("assessment_scope", {}).get("evidence_service"):
        raise ValueError("A vendor and explicit evidence_service are required.")
    evidence = {}
    for item in case["evidence"]:
        eid = item["evidence_id"]
        if eid in evidence:
            raise ValueError(f"Duplicate evidence ID: {eid}")
        evidence[eid] = item
    for item in evidence.values():
        seen = {item["evidence_id"]}
        cursor = item
        while cursor.get("supersedes"):
            previous = cursor["supersedes"]
            if previous in seen or previous not in evidence:
                raise ValueError("Evidence history has a cycle or missing predecessor.")
            seen.add(previous)
            if len(seen) > 2:
                raise ValueError("This lab supports a baseline and one revision; additional assessment rounds require a separate case.")
            parent = evidence[previous]
            if cursor["version"] <= parent["version"]:
                raise ValueError("Evidence revisions must increase the version.")
            cursor = parent
    return evidence


def select_evidence(evidence, root_id, stage):
    current = evidence.get(root_id)
    if current is None or stage == "baseline":
        return current
    while True:
        children = [e for e in evidence.values() if e.get("supersedes") == current["evidence_id"]]
        if not children:
            return current
        if len(children) > 1:
            raise ValueError("Ambiguous evidence revision; choose a single review branch.")
        current = children[0]


def has_scope(items, service):
    return isinstance(items, list) and service.casefold() in {str(v).strip().casefold() for v in items}


def check_evidence(check_id, item, service, as_of, requirements=None):
    if item is None:
        return "unknown", "Required evidence is missing; no passing conclusion is possible."
    try:
        requirements = requirements or {}
        if check_id == "CERT-EXPIRY":
            if requirements.get("vendor_name") and item.get("entity", "").casefold() != requirements["vendor_name"].casefold():
                return "gap", "Certificate names a different entity or omits the assessed entity."
            expiry = date.fromisoformat(item["expiry_date"])
            start = date.fromisoformat(item["valid_from"])
            if start > expiry:
                return "unknown", "Certificate dates are inconsistent."
            if start > as_of:
                return "gap", "The stated validity period has not started."
            if expiry < as_of:
                return "gap", f"Stated validity ended {expiry}; current assurance evidence is unavailable."
            if not has_scope(item.get("service_scope"), service):
                return "gap", "Certificate scope does not cover the assessed service."
            return "pass", "Stated dates and service scope meet the selected checks; authenticity remains unverified."
        if check_id == "ASSURANCE-SCOPE":
            if requirements.get("vendor_name") and item.get("entity", "").casefold() != requirements["vendor_name"].casefold():
                return "gap", "Assurance summary does not identify the assessed vendor entity."
            start = date.fromisoformat(item["report_period_start"])
            end = date.fromisoformat(item["report_period_end"])
            if start > end or end > as_of:
                return "unknown", "Report period is inconsistent or extends beyond the assessment date."
            if (as_of - end).days > requirements.get("report_max_age_days", 365):
                return "gap", "Report period exceeds the lab's documented evidence-age threshold."
            if has_scope(item.get("excluded_services", []), service) or not has_scope(item.get("system_scope"), service):
                return "gap", f"The declared assurance boundary excludes {service}."
            return "pass", "Revised declared scope includes payroll; this check does not authenticate or fully review a SOC report."
        if check_id == "CUSTOMER-MFA":
            if item.get("control_id") != requirements.get("customer_control_id", "CUEC-ADMIN-MFA"):
                return "unknown", "The evidence does not identify the required customer MFA control."
            if requirements.get("customer_iam_owner") and item.get("owner") != requirements["customer_iam_owner"]:
                return "unknown", "The control evidence names a different responsibility owner."
            state = item.get("mfa_enabled")
            if not isinstance(state, bool):
                return "unknown", "MFA enforcement state is missing or not a boolean."
            if not state:
                return "gap", "Required customer-operated administrator MFA is disabled in the mock configuration."
            return "pass", "The revised mock configuration states MFA is enabled; real enforcement is not verified."
        if requirements.get("vendor_name") and item.get("entity", "").casefold() != requirements["vendor_name"].casefold():
            return "gap", "The policy does not identify the assessed vendor entity."
        approved = date.fromisoformat(item["last_approved"])
        if item.get("required_policy_present") is not True or not item.get("policy_owner"):
            return "gap", "The required policy or named owner is missing."
        if approved > as_of or not has_scope(item.get("service_scope"), service):
            return "gap", "The policy approval date or service scope is unsuitable."
        if (as_of - approved).days > requirements.get("policy_max_age_days", 365):
            return "gap", "Policy approval exceeds the lab's documented review-age threshold."
        return "pass", "Policy presence, owner, approval date and payroll scope meet selected checks; operating effectiveness is not tested."
    except (KeyError, TypeError, ValueError):
        return "unknown", "Required metadata is missing or malformed; manual review is needed."


def run_checks(case, stage):
    evidence = validate_case(case)
    service = case["assessment_scope"]["evidence_service"]
    as_of = date.fromisoformat(case["assessment_date"])
    requirements = {**case["assessment_scope"].get("evidence_requirements", {}), "vendor_name": case["vendors"][0]["name"]}
    results = []
    for check_id, root_id, category in CHECKS:
        item = select_evidence(evidence, root_id, stage)
        result, reason = check_evidence(check_id, item, service, as_of, requirements)
        results.append({
            "check_id": check_id, "evidence_id": item["evidence_id"] if item else root_id,
            "category": category, "result": result, "reason": reason,
            "evidence_sha256": digest(item) if item else None,
        })
    return results


def review_context(case):
    return digest({"case_id": case["case_id"], "assessment_date": case["assessment_date"],
                   "vendor": case["vendors"][0], "scope": case["assessment_scope"], "check_version": CHECK_VERSION})


def assess(case, oracle=None, reviews=None, platform=None):
    baseline = run_checks(case, "baseline")
    retest = run_checks(case, "retest")
    retest_by_id = {c["check_id"]: c for c in retest}
    plans = {p["finding_id"]: p for p in case.get("treatment_catalog", [])}
    reviews = reviews or []
    findings, history = [], []
    for check in baseline:
        current = retest_by_id[check["check_id"]]
        if check["result"] == "pass" and current["result"] == "pass":
            continue
        fid = check["check_id"]
        plan = plans.get(fid, {})
        first_failure = current if check["result"] == "pass" else check
        eligible = check["result"] != "pass" and current["result"] == "pass" and current["evidence_id"] != check["evidence_id"]
        matching_reviews = [r for r in reviews if r.get("finding_id") == fid
                            and r.get("context_sha256") == review_context(case)
                            and r.get("baseline_evidence_sha256") == check["evidence_sha256"]
                            and r.get("evidence_sha256") == current["evidence_sha256"]
                            and r.get("evidence_id") == current["evidence_id"]
                            and r.get("decision") == "close"
                            and r.get("reviewer", "").strip() and r.get("reason", "").strip()]
        closed = bool(eligible and matching_reviews)
        status = "Closed in simulation" if closed else "Ready for review" if eligible else "Open"
        findings.append({
            "id": fid, "title": plan.get("title", check["category"] + " evidence gap"),
            "category": check["category"], "owner": plan.get("owner", "Unassigned"),
            "due_date": plan.get("due_date"), "evidence_id": first_failure["evidence_id"],
            "evidence_sha256": first_failure["evidence_sha256"],
            "retest_evidence_id": current["evidence_id"], "retest_evidence_sha256": current["evidence_sha256"],
            "status": status, "baseline_reason": check["reason"], "retest_reason": current["reason"],
            "required_action": plan.get("required_action", "Obtain adequate evidence and record a review."),
            "risk_rating": "Unrated - reviewer judgment required",
        })
        history.append({"event": "Finding recorded", "finding_id": fid, "actor": "Automated metadata check",
                        "reason": first_failure["reason"], "stage": "retest" if check["result"] == "pass" else "baseline", "evidence_id": first_failure["evidence_id"]})
        if eligible:
            history.append({"event": "Retest passed; review required", "finding_id": fid,
                            "actor": "Automated metadata check", "reason": current["reason"],
                            "stage": "retest", "evidence_id": current["evidence_id"]})
        if closed:
            review = matching_reviews[-1]
            history.append({"event": "Simulated closure recorded", "finding_id": fid, "actor": review["reviewer"],
                            "reason": review["reason"], "stage": "review", "evidence_id": current["evidence_id"]})
    detected = {c["check_id"] for c in baseline if c["result"] == "gap"}
    expected = set((oracle or {}).get("initial", {}).get("expected_open_finding_ids", []))
    owner_coverage = sum(f["owner"] != "Unassigned" and bool(f["due_date"]) for f in findings)
    ready = sum(f["status"] in ("Ready for review", "Closed in simulation") for f in findings)
    unresolved = any(f["id"] == "CERT-EXPIRY" and f["status"] == "Open" for f in findings)
    metrics = {
        "seeded_gaps_detected": {"actual": len(detected & expected), "expected": len(expected)},
        "unexpected_gap_ids": sorted(detected - expected) if oracle else [],
        "missed_gap_ids": sorted(expected - detected),
        "clean_fixture_findings": sum(c["evidence_id"] == "E04" and c["result"] != "pass" for c in baseline),
        "owner_due_date_coverage": {"actual": owner_coverage, "expected": len(findings)},
        "retest_checks_passed": {"actual": ready, "expected": len((oracle or {}).get("retest", {}).get("eligible_for_reviewer_closure", []))},
        "reviewer_closures": sum(f["status"] == "Closed in simulation" for f in findings),
        "unresolved_evidence_gap_preserved": unresolved,
        "measurement_scope": "This labelled synthetic fixture and four selected metadata checks only.",
    }
    return {
        "case_id": case["case_id"], "assessment_date": case["assessment_date"],
        "vendor": case["vendors"][0], "notice": case["fictional_data_notice"],
        "criticality": {"tier": "High", "reason": case["assessment_scope"]["business_context"] + " Proposed tier requires reviewer confirmation."},
        "recommendation": {"status": "Hold onboarding", "rationale": "Current assurance remains unverified. Retest passes address selected synthetic checks and do not authorize onboarding.",
                           "conditions": ["Obtain current, authentic, payroll-scoped assurance evidence.", "Review the complete report, exceptions and customer responsibilities.", "An authorized reviewer must record the final onboarding decision."],
                           "human_approval": "Pending"},
        "metrics": metrics, "evidence": case["evidence"], "checks": {"baseline": baseline, "retest": retest},
        "findings": findings, "history": history,
        "communication": {"feedback_status": "Pending peer review", "presentation": "docs/demo_walkthrough.md"},
        "platform": platform or {"name": "CISO Assistant", "status": "Setup in progress", "configuration_executed": False},
        "input_sha256": digest(case), "check_version": CHECK_VERSION, "scope": SCOPE,
    }


def render_memo(result):
    lines = ["# Vendor risk assessment and onboarding recommendation", "", "**SYNTHETIC TRAINING CASE**", "",
             f"Vendor: {result['vendor']['name']} | Assessed: {result['assessment_date']}", "",
             f"## Recommendation: {result['recommendation']['status']}", "",
             "Payroll processes employee identity and bank details. Current supplier assurance is not established, so the recommended lab decision is to hold onboarding pending review.", "",
             "## Risk register findings and responsibilities", ""]
    for f in result["findings"]:
        lines.append(f"- **{f['title']}** - {f['status']}. {f['retest_reason']} Owner: {f['owner']}; due: {f['due_date']}. Evidence: {f['retest_evidence_id']}.")
    lines += ["", "The exported risk register records each finding's status, owner, due date, baseline/retest evidence and required action. Business risk ratings remain unrated pending reviewer judgment; this synthetic third-party risk management (TPRM) exercise does not approve vendor onboarding.", "", "## Decision conditions", ""] + [f"- {c}" for c in result["recommendation"]["conditions"]]
    lines += ["", "## Business tradeoff", "", "Holding onboarding delays the proposed supplier transition. Proceeding without adequate assurance would leave uncertainty over a sensitive payroll service. The business owner and authorized risk reviewer must decide whether to defer, obtain alternative evidence or approve a documented, time-limited exception.", "",
              "## Limits and next review", "", "All documents and configuration states are fictional. Metadata checks do not authenticate certificates, perform a complete SOC review or establish operating effectiveness. Reassess when current evidence arrives or service scope changes. No residual risk reduction or time saving is claimed.", "",
              "## Review status", "", "Human onboarding approval: pending. Peer/mentor feedback: pending. The automated retest cannot close a finding without an explicit, evidence-bound review record.", ""]
    return "\n".join(lines)


def export(result, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "assessment.json", result)
    write_json(output / "results.json", {"case_id": result["case_id"], "input_sha256": result["input_sha256"], "metrics": result["metrics"], "scope": SCOPE})
    write_json(output / "review_history.json", result["history"])
    with (output / "risk_register.csv").open("w", newline="", encoding="utf-8") as handle:
        keys = ["id", "title", "category", "status", "risk_rating", "owner", "due_date", "evidence_id", "retest_evidence_id", "required_action"]
        writer = csv.DictWriter(handle, fieldnames=keys, extrasaction="ignore")
        writer.writeheader()
        for row in result["findings"]:
            # CSV formula injection protection for future user-supplied metadata.
            writer.writerow({k: ("'" + v if isinstance(v, str) and v.startswith(("=", "+", "-", "@")) else v) for k, v in row.items() if k in keys})
    (output / "decision_memo.md").write_text(render_memo(result), encoding="utf-8", newline="\n")
    if result.get("control_review"):
        write_json(output / "control_review.json", result["control_review"])
        coverage = {v["control_id"]: v for v in result["control_review"]["coverage"]}
        with (output / "control_matrix.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["Control ID", "Vendor control question", "NIST CSF 2.0", "ISO 27001:2022 Annex A", "Review status", "Rationale"])
            for control in result["control_review"]["catalog"]["controls"]:
                status = coverage[control["id"]]
                writer.writerow([control["id"], control["question"], "; ".join(control["nist_csf"]), "; ".join(control["iso_27001"]), status["status"], status["reason"]])


def build_control_review():
    catalog = read_json(ROOT / "case-study/control_catalog.json")
    try:
        from control_review import evaluate_controls
        tests = evaluate_controls(ROOT)
    except ImportError:
        tests = {"controls": [], "metrics": {}, "status": "Control tests not installed"}
    links = {"TPRM-IAM-01": ["ITGC-ACCESS"], "TPRM-CHG-01": ["ITGC-CHANGE"], "TPRM-RES-01": ["ITGC-BACKUP"]}
    by_id = {c["id"]: c for c in tests.get("controls", [])}
    coverage = []
    for control in catalog["controls"]:
        ids = links.get(control["id"], [])
        selected = [by_id[i] for i in ids if i in by_id]
        if selected:
            current_exceptions = sum(c["retest_count"] for c in selected)
            status = "Control gap" if current_exceptions else "Retest ready"
            reason = f"{sum(c['baseline_count'] for c in selected)} baseline exception(s); {current_exceptions} remain in the revised synthetic records. These tests cover selected checks only; full control-question evidence and reviewer approval remain outstanding."
        elif control["id"] in ("TPRM-GOV-01", "TPRM-GOV-02", "TPRM-REV-01"):
            status = "Documented"
            reason = "The case documents proposed criticality, ownership and review steps. An authorized reviewer has not approved these lab decisions."
        else:
            status = "Evidence needed"
            reason = "No adequate supplier evidence for this question is included. Request and review the listed evidence before reaching a conclusion."
        coverage.append({"control_id": control["id"], "status": status, "reason": reason, "test_ids": ids})
    return {"catalog": catalog, "tests": tests, "coverage": coverage,
            "scope": "Proposed framework references and selected synthetic vendor IT-control tests; no certification or full-framework compliance conclusion."}


def record_review(case, reviews, finding_id, reviewer, reason):
    if not reviewer.strip() or len(reason.strip()) < 12:
        raise ValueError("Reviewer and a meaningful review reason are required.")
    check = next((c for c in run_checks(case, "retest") if c["check_id"] == finding_id), None)
    baseline = next((c for c in run_checks(case, "baseline") if c["check_id"] == finding_id), None)
    if check is None or baseline is None or baseline["result"] == "pass" or check["result"] != "pass" or check["evidence_id"] == baseline["evidence_id"]:
        raise ValueError("Closure requires a failed baseline and a passing revision for this finding.")
    record = {"finding_id": finding_id, "decision": "close", "reviewer": reviewer.strip(), "reason": reason.strip(),
              "evidence_id": check["evidence_id"], "evidence_sha256": check["evidence_sha256"],
              "context_sha256": review_context(case), "baseline_evidence_sha256": baseline["evidence_sha256"],
              "recorded_at": datetime.now(timezone.utc).isoformat(), "review_scope": "Local synthetic-lab review; identity is self-declared."}
    return [*reviews, record]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", type=Path, default=ROOT / "case-study/data.json")
    parser.add_argument("--output", type=Path, default=ROOT / "output")
    parser.add_argument("--close", metavar="FINDING_ID")
    parser.add_argument("--reviewer", default="")
    parser.add_argument("--reason", default="")
    args = parser.parse_args()
    case = read_json(args.case)
    review_path = args.output / "reviews.json"
    reviews = read_json(review_path) if review_path.exists() else []
    if args.close:
        reviews = record_review(case, reviews, args.close, args.reviewer, args.reason)
        write_json(review_path, reviews)
    platform_path = ROOT / "platform/status.json"
    platform = read_json(platform_path) if platform_path.exists() else None
    oracle_path = args.case.parent / "expected_checks.json"
    result = assess(case, read_json(oracle_path) if oracle_path.exists() else None, reviews, platform)
    if (ROOT / "case-study/control_catalog.json").exists():
        result["control_review"] = build_control_review()
    export(result, args.output)
    print(json.dumps({"case_id": result["case_id"], "output": str(args.output), "metrics": result["metrics"]}, indent=2))


if __name__ == "__main__":
    main()
