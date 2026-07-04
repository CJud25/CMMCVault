"""Unit tests for the SPRS scoring engine. Run: python3 -m unittest discover tests -v"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from logic.catalog import controls, load_sample
from logic.scoring import (
    IMPLEMENTED, NOT_IMPLEMENTED, PARTIAL_ALT, NA_NOT_PERMITTED,
    InvalidStatus, deduction_for, fastest_path, family_rollup,
    floor_score, score_assessment,
)

CAT = controls()
BY_ID = {c["id"]: c for c in CAT}


def all_status(status):
    return {c["id"]: status for c in CAT}


class TestCatalogIntegrity(unittest.TestCase):
    def test_counts_and_floor(self):
        self.assertEqual(len(CAT), 110)
        self.assertEqual(floor_score(CAT), -203)
        fives = sum(1 for c in CAT if c["weight"] in (5, "5/3"))
        threes = sum(1 for c in CAT if c["weight"] == 3)
        ones = sum(1 for c in CAT if c["weight"] == 1)
        nas = [c["id"] for c in CAT if c["weight"] == "NA"]
        self.assertEqual((fives, threes, ones), (44, 14, 51))
        self.assertEqual(nas, ["3.12.4"])


class TestScoring(unittest.TestCase):
    def test_perfect_score(self):
        r = score_assessment(all_status(IMPLEMENTED), CAT)
        self.assertEqual(r.score, 110)
        self.assertEqual(r.open_count, 0)
        self.assertFalse(r.ssp_missing)
        self.assertEqual(r.points_to_threshold, 0)

    def test_floor_score_everything_open(self):
        r = score_assessment(all_status(NOT_IMPLEMENTED), CAT)
        self.assertEqual(r.score, -203)
        self.assertTrue(r.ssp_missing)

    def test_unanswered_defaults_to_not_implemented(self):
        r = score_assessment({}, CAT)
        self.assertEqual(r.score, -203)

    def test_mfa_partial_is_three_points(self):
        a = all_status(IMPLEMENTED)
        a["3.5.3"] = PARTIAL_ALT
        self.assertEqual(score_assessment(a, CAT).score, 107)
        a["3.5.3"] = NOT_IMPLEMENTED
        self.assertEqual(score_assessment(a, CAT).score, 105)

    def test_fips_partial_is_three_points(self):
        a = all_status(IMPLEMENTED)
        a["3.13.11"] = PARTIAL_ALT
        self.assertEqual(score_assessment(a, CAT).score, 107)

    def test_conditional_na_scores_as_implemented(self):
        a = all_status(IMPLEMENTED)
        for cid in ("3.1.12", "3.1.13", "3.1.16", "3.1.17", "3.1.18"):
            a[cid] = NA_NOT_PERMITTED
        self.assertEqual(score_assessment(a, CAT).score, 110)

    def test_partial_rejected_on_normal_control(self):
        with self.assertRaises(InvalidStatus):
            deduction_for(BY_ID["3.1.1"], PARTIAL_ALT)

    def test_na_rejected_on_non_conditional_control(self):
        with self.assertRaises(InvalidStatus):
            deduction_for(BY_ID["3.8.7"], NA_NOT_PERMITTED)

    def test_ssp_missing_flag_but_zero_numeric_weight(self):
        a = all_status(IMPLEMENTED)
        a["3.12.4"] = NOT_IMPLEMENTED
        r = score_assessment(a, CAT)
        self.assertTrue(r.ssp_missing)
        self.assertEqual(r.score, 110)  # numeric unchanged; validity flag carries the message


class TestFastestPath(unittest.TestCase):
    def test_sample_reaches_threshold(self):
        sample = load_sample()
        r = score_assessment(sample["statuses"], CAT)
        self.assertTrue(30 <= r.score <= 65, f"sample score {r.score} outside demo range")
        steps = fastest_path(sample["statuses"], CAT)
        self.assertTrue(steps[-1]["reaches_target"])
        gains = [s["gain"] for s in steps if not s["required_first"]]
        self.assertEqual(gains, sorted(gains, reverse=True))

    def test_ssp_forced_first_when_missing(self):
        a = all_status(IMPLEMENTED)
        a["3.12.4"] = NOT_IMPLEMENTED
        a["3.8.7"] = NOT_IMPLEMENTED
        steps = fastest_path(a, CAT)
        self.assertEqual(steps[0]["id"], "3.12.4")
        self.assertTrue(steps[0]["required_first"])


class TestFamilyRollup(unittest.TestCase):
    def test_rollup_totals(self):
        rows = family_rollup(all_status(IMPLEMENTED), CAT)
        self.assertEqual(len(rows), 14)
        self.assertEqual(sum(r["controls"] for r in rows), 110)
        self.assertEqual(sum(r["points_possible"] for r in rows), 313)
        self.assertTrue(all(r["points_lost"] == 0 for r in rows))


if __name__ == "__main__":
    unittest.main()
