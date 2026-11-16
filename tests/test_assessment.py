import copy
from datetime import date
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from assessment import assess, check_evidence, read_json, record_review, run_checks


class VendorReviewTests(unittest.TestCase):
    def setUp(self):
        self.case = read_json(ROOT / "case-study/data.json")
        self.oracle = read_json(ROOT / "case-study/expected_checks.json")

    def test_seeded_gaps_detected_and_clean_policy_not_flagged(self):
        result = assess(self.case, self.oracle)
        self.assertEqual({f["id"] for f in result["findings"]}, {"CERT-EXPIRY", "ASSURANCE-SCOPE", "CUSTOMER-MFA"})
        self.assertEqual(result["metrics"]["clean_fixture_findings"], 0)
        self.assertEqual(result["metrics"]["seeded_gaps_detected"], {"actual": 3, "expected": 3})

    def test_retest_does_not_close_findings_or_approve_vendor(self):
        result = assess(self.case, self.oracle)
        self.assertEqual([f["status"] for f in result["findings"]], ["Open", "Ready for review", "Ready for review"])
        self.assertEqual(result["metrics"]["reviewer_closures"], 0)
        self.assertEqual(result["recommendation"]["human_approval"], "Pending")

    def test_fully_clean_baseline_produces_no_findings(self):
        for e in self.case["evidence"]:
            if e["evidence_id"] == "E01":
                e["expiry_date"] = "2027-10-31"
            elif e["evidence_id"] == "E02":
                e["system_scope"] = ["Payroll processing"]
                e["excluded_services"] = []
            elif e["evidence_id"] == "E03":
                e["mfa_enabled"] = True
        self.assertEqual(assess(self.case)["findings"], [])

    def test_changing_answer_key_cannot_change_detection(self):
        normal = assess(self.case, self.oracle)
        self.oracle["initial"]["expected_open_finding_ids"] = ["FAKE-ORACLE"]
        changed = assess(self.case, self.oracle)
        self.assertEqual(normal["checks"], changed["checks"])
        self.assertEqual(normal["findings"], changed["findings"])

    def test_missing_evidence_fails_closed_without_fabricating_a_pass(self):
        self.case["evidence"] = [e for e in self.case["evidence"] if e["evidence_id"] not in ("E03", "E03-v2")]
        result = assess(self.case)
        check = next(c for c in result["checks"]["baseline"] if c["check_id"] == "CUSTOMER-MFA")
        self.assertEqual(check["result"], "unknown")
        self.assertIn("CUSTOMER-MFA", [f["id"] for f in result["findings"]])

    def test_expiry_is_inclusive_and_future_start_not_valid(self):
        item = copy.deepcopy(self.case["evidence"][0])
        item["expiry_date"] = "2026-11-16"
        self.assertEqual(check_evidence("CERT-EXPIRY", item, "Payroll processing", date(2026, 11, 16))[0], "pass")
        item.update(valid_from="2026-11-17", expiry_date="2027-11-16")
        self.assertEqual(check_evidence("CERT-EXPIRY", item, "Payroll processing", date(2026, 11, 16))[0], "gap")

    def test_unknown_mfa_string_is_not_treated_as_true(self):
        item = {"control_id": "CUEC-ADMIN-MFA", "mfa_enabled": "false"}
        self.assertEqual(check_evidence("CUSTOMER-MFA", item, "Payroll processing", date(2026, 11, 16))[0], "unknown")

    def test_scope_exclusion_wins_over_inclusion(self):
        item = copy.deepcopy(self.case["evidence"][1])
        item["system_scope"] = ["Payroll processing"]
        self.assertEqual(check_evidence("ASSURANCE-SCOPE", item, "Payroll processing", date(2026, 11, 16))[0], "gap")

    def test_malformed_report_dates_are_unknown(self):
        item = copy.deepcopy(self.case["evidence"][1])
        item["report_period_start"] = "not-a-date"
        self.assertEqual(check_evidence("ASSURANCE-SCOPE", item, "Payroll processing", date(2026, 11, 16))[0], "unknown")

    def test_closure_requires_passing_revision_and_reason(self):
        with self.assertRaises(ValueError):
            record_review(self.case, [], "CERT-EXPIRY", "Test reviewer", "Checked replacement evidence.")
        with self.assertRaises(ValueError):
            record_review(self.case, [], "ASSURANCE-SCOPE", "", "Checked replacement evidence.")
        reviews = record_review(self.case, [], "ASSURANCE-SCOPE", "Test reviewer", "Reviewed corrected scope in the synthetic revision.")
        result = assess(self.case, self.oracle, reviews)
        self.assertEqual(result["findings"][1]["status"], "Closed in simulation")
        self.assertEqual(result["findings"][0]["status"], "Open")

    def test_changed_evidence_invalidates_previous_review(self):
        reviews = record_review(self.case, [], "ASSURANCE-SCOPE", "Test reviewer", "Reviewed corrected scope in the synthetic revision.")
        next(e for e in self.case["evidence"] if e["evidence_id"] == "E02-v2")["review_note"] += " New material."
        self.assertEqual(assess(self.case, self.oracle, reviews)["findings"][1]["status"], "Ready for review")

    def test_ambiguous_revision_is_rejected(self):
        extra = copy.deepcopy(next(e for e in self.case["evidence"] if e["evidence_id"] == "E02-v2"))
        extra["evidence_id"] = "E02-alternative"
        self.case["evidence"].append(extra)
        with self.assertRaises(ValueError):
            run_checks(self.case, "retest")

    def test_cycle_or_duplicate_id_is_rejected(self):
        self.case["evidence"][0]["supersedes"] = "E01"
        with self.assertRaises(ValueError):
            run_checks(self.case, "baseline")
        self.case["evidence"][0].pop("supersedes")
        self.case["evidence"].append(copy.deepcopy(self.case["evidence"][0]))
        with self.assertRaises(ValueError):
            run_checks(self.case, "baseline")

    def test_repeated_assessment_is_deterministic(self):
        self.assertEqual(assess(self.case, self.oracle), assess(copy.deepcopy(self.case), copy.deepcopy(self.oracle)))

    def test_new_retest_failure_is_added_even_when_baseline_passed(self):
        policy = copy.deepcopy(next(e for e in self.case["evidence"] if e["evidence_id"] == "E04"))
        policy.update(evidence_id="E04-v2", version=2, supersedes="E04", required_policy_present=False)
        self.case["evidence"].append(policy)
        result = assess(self.case, self.oracle)
        finding = next(f for f in result["findings"] if f["id"] == "POLICY-CHECK")
        self.assertEqual(finding["status"], "Open")
        self.assertEqual(finding["evidence_id"], "E04-v2")
        self.assertTrue(any(e["finding_id"] == "POLICY-CHECK" and e["stage"] == "retest" for e in result["history"]))

    def test_closure_is_not_reused_for_a_different_case_vendor_or_scope(self):
        reviews = record_review(self.case, [], "ASSURANCE-SCOPE", "Test reviewer", "Reviewed corrected scope in the synthetic revision.")
        for kind in ("case", "vendor", "scope", "date"):
            changed = copy.deepcopy(self.case)
            if kind == "case":
                changed["case_id"] = "OTHER-CASE"
            elif kind == "vendor":
                changed["vendors"][0]["vendor_id"] = "OTHER-VENDOR"
            elif kind == "scope":
                changed["assessment_scope"]["business_context"] += " Material scope change."
            else:
                changed["assessment_date"] = "2026-11-17"
            self.assertEqual(assess(changed, self.oracle, reviews)["findings"][1]["status"], "Ready for review")

    def test_wrong_certificate_entity_and_mfa_control_are_not_accepted(self):
        cert = next(e for e in self.case["evidence"] if e["evidence_id"] == "E01")
        cert.update(expiry_date="2027-10-31", entity="Wrong vendor")
        mfa = next(e for e in self.case["evidence"] if e["evidence_id"] == "E03-v2")
        mfa["control_id"] = "OTHER-CONTROL"
        result = assess(self.case, self.oracle)
        self.assertEqual(result["checks"]["retest"][0]["result"], "gap")
        self.assertEqual(result["findings"][2]["status"], "Open")
        mfa["control_id"] = "CUEC-ADMIN-MFA"
        mfa["owner"] = "Different customer"
        self.assertEqual(assess(self.case)["checks"]["retest"][2]["result"], "unknown")

    def test_stale_policy_and_report_fail_configured_freshness_rules(self):
        policy = next(e for e in self.case["evidence"] if e["evidence_id"] == "E04")
        policy["last_approved"] = "1900-01-01"
        report = next(e for e in self.case["evidence"] if e["evidence_id"] == "E02-v2")
        report.update(report_period_start="1900-01-01", report_period_end="1900-12-31")
        checks = run_checks(self.case, "retest")
        self.assertEqual(checks[1]["result"], "gap")
        self.assertEqual(checks[3]["result"], "gap")

    def test_third_evidence_round_is_rejected_not_silently_collapsed(self):
        item = copy.deepcopy(next(e for e in self.case["evidence"] if e["evidence_id"] == "E02-v2"))
        item.update(evidence_id="E02-v3", supersedes="E02-v2", version=3)
        self.case["evidence"].append(item)
        with self.assertRaisesRegex(ValueError, "baseline and one revision"):
            assess(self.case)

    def test_report_and_policy_must_identify_the_assessed_vendor(self):
        report = next(e for e in self.case["evidence"] if e["evidence_id"] == "E02-v2")
        report["entity"] = "Other supplier"
        self.assertEqual(run_checks(self.case, "retest")[1]["result"], "gap")
        report.pop("entity")
        self.assertEqual(run_checks(self.case, "retest")[1]["result"], "gap")
        policy = next(e for e in self.case["evidence"] if e["evidence_id"] == "E04")
        policy["entity"] = "Other supplier"
        self.assertEqual(run_checks(self.case, "baseline")[3]["result"], "gap")


if __name__ == "__main__":
    unittest.main()
