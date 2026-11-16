import copy
import json
import unittest
from pathlib import Path

from scripts.validate_framework_snapshot import canonical_json_sha256, validate


ROOT = Path(__file__).resolve().parents[1]


class FrameworkSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.catalog = json.loads((ROOT / "case-study/control_catalog.json").read_text(encoding="utf-8"))
        self.snapshot = json.loads((ROOT / "output/framework_links.json").read_text(encoding="utf-8"))

    def assert_invalid(self, catalog=None, snapshot=None):
        with self.assertRaises(ValueError):
            validate(catalog if catalog is not None else self.catalog,
                     snapshot if snapshot is not None else self.snapshot)

    def test_checked_in_recorded_readback_is_consistent(self):
        validate(self.catalog, self.snapshot)

    def test_stale_catalog_hash_and_catalog_id_are_rejected(self):
        changed = copy.deepcopy(self.catalog)
        changed["controls"][0]["title"] += " changed"
        self.assert_invalid(catalog=changed)
        changed_snapshot = copy.deepcopy(self.snapshot)
        changed_snapshot["catalog_id"] = "other-catalog"
        self.assert_invalid(snapshot=changed_snapshot)

    def test_duplicate_or_missing_link_is_rejected(self):
        duplicate = copy.deepcopy(self.snapshot)
        duplicate["links"].append(copy.deepcopy(duplicate["links"][0]))
        duplicate["linked_question_count"] = 11
        self.assert_invalid(snapshot=duplicate)
        missing = copy.deepcopy(self.snapshot)
        missing["links"].pop()
        self.assert_invalid(snapshot=missing)

    def test_wrong_native_reference_and_missing_record_id_are_rejected(self):
        mismatch = copy.deepcopy(self.snapshot)
        next(link for link in mismatch["links"] if link["question_id"] == "TPRM-GOV-01")["native_ref_id"] = "A.5.20"
        self.assert_invalid(snapshot=mismatch)
        missing_id = copy.deepcopy(self.snapshot)
        missing_id["links"][0]["native_record_id"] = ""
        self.assert_invalid(snapshot=missing_id)

    def test_distinct_native_references_cannot_share_one_record_id(self):
        changed = copy.deepcopy(self.snapshot)
        first = changed["links"][0]["native_record_id"]
        next(link for link in changed["links"]
             if link["native_ref_id"] != changed["links"][0]["native_ref_id"])["native_record_id"] = first
        self.assert_invalid(snapshot=changed)

    def test_premature_status_changes_are_rejected(self):
        for key, value in (("assessment_status", "approved"),
                           ("findings_assessment_status", "completed"),
                           ("all_scoped_controls_remain_to_do", False),
                           ("assessment_and_finding_states_unchanged", False),
                           ("finding_status_counts", {"resolved": 3})):
            changed = copy.deepcopy(self.snapshot)
            changed[key] = value
            with self.subTest(key=key):
                self.assert_invalid(snapshot=changed)
        changed = copy.deepcopy(self.snapshot)
        changed["links"][0]["status"] = "implemented"
        self.assert_invalid(snapshot=changed)

    def test_canonical_digest_is_line_ending_independent(self):
        value = {"catalog_id": "sample", "controls": [{"id": "one"}]}
        lf = json.dumps(value, indent=2, ensure_ascii=False).encode("utf-8")
        crlf = lf.replace(b"\n", b"\r\n")
        self.assertNotEqual(lf, crlf)
        self.assertEqual(canonical_json_sha256(json.loads(lf)),
                         canonical_json_sha256(json.loads(crlf)))


if __name__ == "__main__":
    unittest.main()
