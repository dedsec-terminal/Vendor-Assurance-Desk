import copy
import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_scorecard import build, canonical_json_sha256


ROOT = Path(__file__).resolve().parents[1]


class ScorecardTests(unittest.TestCase):
    def setUp(self):
        self.assessment = json.loads((ROOT / "output/assessment.json").read_text(encoding="utf-8"))
        self.review = json.loads((ROOT / "output/control_review.json").read_text(encoding="utf-8"))
        self.tmp = tempfile.TemporaryDirectory()
        self.platform = Path(self.tmp.name) / "platform_sync.json"

    def tearDown(self):
        self.tmp.cleanup()

    @property
    def source_hashes(self):
        return {"assessment.json": canonical_json_sha256(ROOT / "output/assessment.json"),
                "control_review.json": canonical_json_sha256(ROOT / "output/control_review.json")}

    def test_fixture_deltas_and_scope_are_explicit(self):
        out = build(self.assessment, self.review, self.platform)
        self.assertEqual(out["scope"], {"vendors": 1, "metadata_checks": 4, "itgc_controls": 3,
                                       "synthetic_only": True, "overall_maturity_score": None})
        self.assertEqual((out["metadata_check_outcomes"]["baseline_gaps"],
                          out["metadata_check_outcomes"]["retest_gaps"],
                          out["metadata_check_outcomes"]["gap_delta"]), (3, 1, -2))
        self.assertEqual((out["itgc_outcomes"]["baseline_exception_count"],
                          out["itgc_outcomes"]["retest_exception_count"],
                          out["itgc_outcomes"]["exception_delta"]), (3, 2, -1))
        self.assertEqual(out["itgc_outcomes"]["current_exposures_unresolved"], 1)
        self.assertEqual(out["itgc_outcomes"]["historical_exceptions_preserved"], 2)
        self.assertEqual(out["human_review"]["status"], "Pending peer review")

    def test_missing_snapshot_stays_pending(self):
        self.assertEqual(build(self.assessment, self.review, self.platform)["platform_roundtrip"]["status"], "pending")

    def test_wrong_case_hash_or_vendor_is_invalid_and_uncredited(self):
        wrong = {"case_id": self.assessment["case_id"], "input_sha256": self.assessment["input_sha256"],
                 "vendor_id": self.assessment["vendor"]["vendor_id"], "service_id": "svc-1",
                 "assessment_id": "asmt-1", "links_verified": True,
                 "source_hash_format": "canonical-json-v1",
                 "link_counts": {"vendor": 1, "service": 1, "assessment": 1, "applied_controls": 4,
                                 "findings": 3, "evidence": 6, "unique_applied_controls": 3,
                                 "supplier_scope_controls": 10}, "source_file_sha256": self.source_hashes}
        for key, value in (("case_id", "OTHER"), ("input_sha256", "0" * 64), ("vendor_id", "OTHER")):
            sample = copy.deepcopy(wrong)
            sample[key] = value
            self.platform.write_text(json.dumps(sample), encoding="utf-8")
            result = build(self.assessment, self.review, self.platform, self.source_hashes)["platform_roundtrip"]
            self.assertEqual(result["status"], "invalid")
            self.assertIsNone(result["counts"])

    def test_missing_platform_ids_and_negative_counts_are_not_verified(self):
        sample = {"case_id": self.assessment["case_id"], "input_sha256": self.assessment["input_sha256"],
                  "vendor_id": self.assessment["vendor"]["vendor_id"], "links_verified": True,
                  "source_hash_format": "canonical-json-v1",
                  "link_counts": {"vendor": 1, "service": 1, "assessment": 1, "applied_controls": 4,
                                  "findings": 3, "evidence": 6, "unique_applied_controls": 3,
                                  "supplier_scope_controls": 10}, "source_file_sha256": self.source_hashes}
        self.platform.write_text(json.dumps(sample), encoding="utf-8")
        self.assertEqual(build(self.assessment, self.review, self.platform, self.source_hashes)["platform_roundtrip"]["status"], "invalid")
        sample.update(service_id="svc-1", assessment_id="asmt-1")
        sample["link_counts"]["applied_controls"] = -1
        self.platform.write_text(json.dumps(sample), encoding="utf-8")
        self.assertEqual(build(self.assessment, self.review, self.platform, self.source_hashes)["platform_roundtrip"]["status"], "invalid")

    def test_identity_hash_matched_verified_counts_are_reported(self):
        sample = {"case_id": self.assessment["case_id"], "input_sha256": self.assessment["input_sha256"],
                  "vendor_id": self.assessment["vendor"]["vendor_id"], "service_id": "svc-1",
                  "assessment_id": "asmt-1", "links_verified": True,
                  "source_hash_format": "canonical-json-v1",
                  "link_counts": {"vendor": 1, "service": 1, "assessment": 1, "applied_controls": 4,
                                  "findings": 3, "evidence": 6, "unique_applied_controls": 3,
                                  "supplier_scope_controls": 10}, "source_file_sha256": self.source_hashes}
        self.platform.write_text(json.dumps(sample), encoding="utf-8")
        result = build(self.assessment, self.review, self.platform, self.source_hashes)["platform_roundtrip"]
        self.assertEqual(result["status"], "verified")
        self.assertEqual(result["counts"]["applied_controls"], 4)
        self.assertEqual(result["counts"]["unique_applied_controls"], 3)
        self.assertEqual(result["counts"]["supplier_scope_controls"], 10)

    def test_stale_source_artifact_hash_is_invalid(self):
        sample = {"case_id": self.assessment["case_id"], "input_sha256": self.assessment["input_sha256"],
                  "vendor_id": self.assessment["vendor"]["vendor_id"], "service_id": "svc-1",
                  "assessment_id": "asmt-1", "links_verified": True,
                  "source_hash_format": "canonical-json-v1",
                  "link_counts": {"vendor": 1, "service": 1, "assessment": 1, "applied_controls": 4,
                                  "findings": 3, "evidence": 6, "unique_applied_controls": 3,
                                  "supplier_scope_controls": 10},
                  "source_file_sha256": {**self.source_hashes, "control_review.json": "0" * 64}}
        self.platform.write_text(json.dumps(sample), encoding="utf-8")
        result = build(self.assessment, self.review, self.platform, self.source_hashes)["platform_roundtrip"]
        self.assertEqual(result["status"], "invalid")
        self.assertIsNone(result["counts"])

    def test_incomparable_metadata_checks_fail_closed(self):
        altered = copy.deepcopy(self.assessment)
        altered["checks"]["retest"].pop()
        with self.assertRaises(ValueError):
            build(altered, self.review, self.platform)


if __name__ == "__main__":
    unittest.main()
