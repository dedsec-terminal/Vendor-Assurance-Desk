import csv
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from control_review import evaluate_controls


class ControlReviewTests(unittest.TestCase):
    def test_detects_one_seeded_exception_per_control_without_flagging_clean_rows(self):
        result = evaluate_controls(ROOT)
        self.assertEqual(result["assessment_date"], "2026-11-16")
        self.assertEqual(result["metrics"]["seeded_failures_detected"], {"actual": 3, "expected": 3})
        self.assertEqual(result["metrics"]["clean_rows_flagged"], 0)
        for control in result["controls"]:
            self.assertEqual(control["baseline_population"], 2)
            self.assertEqual(control["baseline_exception_count"], 1)
            self.assertEqual(control["baseline_exceptions"][0]["fixture_role"], "seeded_exception")

    def test_retest_fixes_access_and_backup_but_keeps_historical_change_gap_open(self):
        result = evaluate_controls(ROOT)
        by_id = {control["id"]: control for control in result["controls"]}
        self.assertEqual(by_id["ITGC-ACCESS"]["status"], "gap")
        self.assertTrue(by_id["ITGC-ACCESS"]["current_exposure_resolved"])
        self.assertTrue(any("login is recorded after termination" in r for r in by_id["ITGC-ACCESS"]["retest_exceptions"][0]["reasons"]))
        self.assertEqual(by_id["ITGC-BACKUP"]["status"], "pass")
        self.assertTrue(by_id["ITGC-BACKUP"]["current_exposure_resolved"])
        self.assertEqual(by_id["ITGC-CHANGE"]["status"], "gap")
        self.assertIn("deployed before approval", by_id["ITGC-CHANGE"]["retest_exceptions"][0]["reasons"][0])
        self.assertEqual(result["metrics"]["retest_exceptions_remaining"], 2)
        self.assertIn("no exception is closed", result["human_review"])

    def test_retests_preserve_access_history_and_use_a_new_backup_observation(self):
        access_base = ROOT / "case-study/itgc/ITGC-ACCESS/baseline/access_population.csv"
        access_retest = ROOT / "case-study/itgc/ITGC-ACCESS/retest/access_population.csv"
        with access_base.open(newline="", encoding="utf-8") as handle:
            baseline = list(csv.DictReader(handle))[0]
        with access_retest.open(newline="", encoding="utf-8") as handle:
            retest = list(csv.DictReader(handle))[0]
        self.assertEqual(retest["termination_date"], baseline["termination_date"])
        self.assertEqual(retest["last_login_date"], baseline["last_login_date"])
        self.assertEqual(retest["last_login_date"], "2026-11-12")
        self.assertEqual(retest["access_removed_date"], "2026-11-16")
        with (ROOT / "case-study/itgc/ITGC-BACKUP/baseline/backup_population.csv").open(newline="", encoding="utf-8") as handle:
            backup_base = list(csv.DictReader(handle))[0]
        with (ROOT / "case-study/itgc/ITGC-BACKUP/retest/backup_population.csv").open(newline="", encoding="utf-8") as handle:
            backup_retest = list(csv.DictReader(handle))[0]
        self.assertEqual(backup_base["record_id"], "BKP-301")
        self.assertEqual(backup_base["backup_status"], "Failed")
        self.assertEqual(backup_retest["record_id"], "BKP-303")
        self.assertEqual(backup_retest["scheduled_date"], "2026-11-16")

    def _copy_fixture(self):
        temp = tempfile.TemporaryDirectory()
        target = Path(temp.name) / "case"
        shutil.copytree(ROOT / "case-study", target / "case-study")
        return temp, target

    def test_malformed_required_date_is_an_exception_not_a_pass(self):
        temp, target = self._copy_fixture()
        self.addCleanup(temp.cleanup)
        access = target / "case-study/itgc/ITGC-ACCESS/retest/access_population.csv"
        with access.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
            fields = rows[0].keys()
        rows[0]["last_login_date"] = "not-a-date"
        with access.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        result = evaluate_controls(target)
        control = next(c for c in result["controls"] if c["id"] == "ITGC-ACCESS")
        self.assertEqual(control["status"], "gap")
        self.assertTrue(any("last_login_date" in reason for reason in control["retest_exceptions"][0]["reasons"]))

    def test_future_evidence_date_is_flagged(self):
        temp, target = self._copy_fixture()
        self.addCleanup(temp.cleanup)
        change = target / "case-study/itgc/ITGC-CHANGE/retest/change_population.csv"
        with change.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
            fields = rows[0].keys()
        rows[1]["approval_date"] = "2026-11-17"
        with change.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        result = evaluate_controls(target)
        control = next(c for c in result["controls"] if c["id"] == "ITGC-CHANGE")
        self.assertTrue(any("after the fixed assessment date" in reason for e in control["retest_exceptions"] for reason in e["reasons"]))

    def test_missing_population_fails_closed(self):
        temp, target = self._copy_fixture()
        self.addCleanup(temp.cleanup)
        (target / "case-study/itgc/ITGC-BACKUP/retest/backup_population.csv").unlink()
        with self.assertRaises(FileNotFoundError):
            evaluate_controls(target)

    def test_mismatched_vendor_scope_is_rejected(self):
        temp, target = self._copy_fixture()
        self.addCleanup(temp.cleanup)
        access = target / "case-study/itgc/ITGC-ACCESS/baseline/access_population.csv"
        with access.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
            fields = rows[0].keys()
        rows[0]["vendor_id"] = "OTHER-VENDOR"
        with access.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        with self.assertRaisesRegex(ValueError, "Vendor scope mismatch"):
            evaluate_controls(target)

    def test_seeded_detection_metric_tracks_missing_detected_control(self):
        temp, target = self._copy_fixture()
        self.addCleanup(temp.cleanup)
        access = target / "case-study/itgc/ITGC-ACCESS/baseline/access_population.csv"
        with access.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
            fields = rows[0].keys()
        # It still raises an exception, but not the expected post-termination
        # login finding; an unrelated false positive must not count as detection.
        rows[0]["last_login_date"] = "bad-date"
        with access.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        result = evaluate_controls(target)
        self.assertEqual(result["metrics"]["seeded_failures_detected"], {"actual": 2, "expected": 3})
        self.assertEqual(result["metrics"]["seeded_failures_missed"], ["ITGC-ACCESS"])


if __name__ == "__main__":
    unittest.main()
