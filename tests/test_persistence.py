"""Tests for validated JSON import (untrusted-file hardening)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from logic.catalog import controls
from logic.scoring import NOT_IMPLEMENTED, PARTIAL_ALT, score_assessment
from persistence import sanitize_import, sanitize_uri

CAT = controls()


class TestSanitizeImport(unittest.TestCase):
    def test_invalid_status_coerced(self):
        # partial_alt is not valid on a normal control -> coerced, warned
        payload = {"statuses": {"3.1.1": "partial_alt", "3.5.3": "partial_alt"}}
        state, warns = sanitize_import(payload, CAT)
        self.assertEqual(state["assessment"]["3.1.1"], NOT_IMPLEMENTED)
        self.assertEqual(state["assessment"]["3.5.3"], PARTIAL_ALT)  # valid on MFA
        self.assertTrue(any("3.1.1" in w for w in warns))

    def test_unknown_id_dropped(self):
        payload = {"statuses": {"9.9.9": "implemented"}}
        state, warns = sanitize_import(payload, CAT)
        self.assertNotIn("9.9.9", state["assessment"])
        self.assertTrue(any("9.9.9" in w for w in warns))

    def test_all_110_present_after_import(self):
        state, _ = sanitize_import({"statuses": {}}, CAT)
        self.assertEqual(len(state["assessment"]), 110)

    def test_bad_poam_date_dropped(self):
        payload = {"poam": {"3.1.1": {"target_date": "not-a-date"}}}
        state, warns = sanitize_import(payload, CAT)
        self.assertNotIn("3.1.1", state["poam"])
        self.assertTrue(any("invalid POA&M date" in w for w in warns))

    def test_score_is_not_trusted(self):
        # embedded score is ignored; recomputed value governs
        payload = {"statuses": {c["id"]: "implemented" for c in CAT}, "score": -999}
        state, _ = sanitize_import(payload, CAT)
        self.assertEqual(score_assessment(state["assessment"], CAT).score, 110)

    def test_legacy_evidence_filenames_migrated(self):
        payload = {"evidence": {"3.10.1": ["badge-policy.pdf", "log.xlsx"]}}
        state, warns = sanitize_import(payload, CAT)
        entries = state["evidence"]["3.10.1"]
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["title"], "badge-policy.pdf")
        self.assertEqual(entries[0]["doc_status"], "draft")
        self.assertTrue(any("migrated legacy" in w for w in warns))

    def test_unsafe_uri_neutralized(self):
        payload = {"evidence": {"3.10.1": [
            {"title": "x", "location_uri": "javascript:alert(1)"}]}}
        state, _ = sanitize_import(payload, CAT)
        self.assertNotIn("javascript:", state["evidence"]["3.10.1"][0]["location_uri"])

    def test_sanitize_uri(self):
        self.assertEqual(sanitize_uri("https://ok"), "https://ok")
        self.assertNotIn("javascript", sanitize_uri("javascript:bad").lower())

    def test_non_dict_payload(self):
        state, warns = sanitize_import(["nope"], CAT)
        self.assertEqual(len(state["assessment"]), 110)
        self.assertTrue(warns)


if __name__ == "__main__":
    unittest.main()
