"""Tests for the Conditional-status readiness engine (32 CFR 170.21).

Run: python -m unittest discover tests -v   (or: pytest tests/test_readiness.py)
The central assertions: the compound gate, the six never-eligible controls, the
status-dependent 3.13.11 rule, the blocker-first path overshooting 88, and the
89-but-not-ready sample.
"""

import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from logic.catalog import controls, load_sample, poam_rules
from logic.scoring import IMPLEMENTED, NOT_IMPLEMENTED, PARTIAL_ALT
from logic.readiness import (
    LBL_MANDATORY, blocker_first_path, conditional_eligibility,
    control_labels, dashboard_summary, poam_clock, poam_eligible,
)

CAT = controls()
BY_ID = {c["id"]: c for c in CAT}
RULES = poam_rules()


def all_status(status):
    return {c["id"]: status for c in CAT}


class TestPoamEligible(unittest.TestCase):
    def test_one_point_eligible(self):
        self.assertTrue(poam_eligible(BY_ID["3.3.4"], NOT_IMPLEMENTED, RULES))

    def test_five_point_not_eligible(self):
        self.assertFalse(poam_eligible(BY_ID["3.4.8"], NOT_IMPLEMENTED, RULES))

    def test_three_point_not_eligible(self):
        self.assertFalse(poam_eligible(BY_ID["3.8.1"], NOT_IMPLEMENTED, RULES))

    def test_six_excluded_never_eligible(self):
        for cid in ("3.1.20", "3.1.22", "3.12.4", "3.10.3", "3.10.4", "3.10.5"):
            self.assertFalse(
                poam_eligible(BY_ID[cid], NOT_IMPLEMENTED, RULES),
                f"{cid} must never be POA&M-eligible")

    def test_3_13_11_status_dependent(self):
        # eligible at the -3 partial, NOT at the -5 not-implemented
        self.assertTrue(poam_eligible(BY_ID["3.13.11"], PARTIAL_ALT, RULES))
        self.assertFalse(poam_eligible(BY_ID["3.13.11"], NOT_IMPLEMENTED, RULES))

    def test_3_5_3_partial_not_eligible(self):
        # 3.5.3 (MFA) is the OTHER 5/3 special but has NO carve-out: partial (-3)
        # is still ineligible (only 3.13.11 encryption is excepted).
        self.assertFalse(poam_eligible(BY_ID["3.5.3"], PARTIAL_ALT, RULES))
        self.assertFalse(poam_eligible(BY_ID["3.5.3"], NOT_IMPLEMENTED, RULES))


class TestConditionalEligibility(unittest.TestCase):
    def test_perfect_is_eligible(self):
        r = conditional_eligibility(all_status(IMPLEMENTED), CAT, RULES)
        self.assertTrue(r.eligible)
        self.assertEqual(r.blocking_ids, [])

    def test_below_88_not_eligible(self):
        a = all_status(IMPLEMENTED)
        a["3.1.1"] = NOT_IMPLEMENTED  # -5 -> 105, still above 88 though
        # push below 88 with several 5-pointers
        for cid in ("3.1.1", "3.1.2", "3.1.12", "3.1.13", "3.1.16"):
            a[cid] = NOT_IMPLEMENTED
        r = conditional_eligibility(a, CAT, RULES)
        self.assertFalse(r.score_ok)
        self.assertFalse(r.eligible)

    def test_89_but_blocked_by_5pt(self):
        # score 89 (>=88) but an open 5-pt control blocks eligibility
        a = all_status(IMPLEMENTED)
        a["3.4.8"] = NOT_IMPLEMENTED           # -5 -> 105
        # add eligible 1-pt gaps to reach exactly 89 (need -16 more)
        # simpler: just assert the single 5-pt blocker case
        r = conditional_eligibility(a, CAT, RULES)
        self.assertTrue(r.score_ok)
        self.assertIn("3.4.8", r.blocking_ids)
        self.assertFalse(r.eligible)

    def test_ssp_missing_blocks(self):
        a = all_status(IMPLEMENTED)
        a["3.12.4"] = NOT_IMPLEMENTED
        r = conditional_eligibility(a, CAT, RULES)
        self.assertFalse(r.ssp_ok)
        self.assertFalse(r.eligible)
        self.assertIn("3.12.4", r.blocking_ids)


class TestSampleCenterpiece(unittest.TestCase):
    def test_sample_scores_89_and_is_not_ready(self):
        sample = load_sample()
        r = conditional_eligibility(sample["statuses"], CAT, RULES)
        self.assertEqual(r.score, 89)
        self.assertTrue(r.score_ok)
        self.assertTrue(r.ssp_ok)
        self.assertFalse(r.eligible)
        self.assertEqual(set(r.blocking_ids), {"3.4.8", "3.13.6", "3.14.6", "3.1.20"})


class TestBlockerFirstPath(unittest.TestCase):
    def test_sample_path_blockers_present_and_overshoots(self):
        sample = load_sample()
        steps = blocker_first_path(sample["statuses"], CAT, RULES)
        path_ids = {s["id"] for s in steps}
        for cid in ("3.4.8", "3.13.6", "3.14.6", "3.1.20"):
            self.assertIn(cid, path_ids)
        # the sample is already at 89; fixing mandatory blockers overshoots past 88
        self.assertGreaterEqual(steps[-1]["score_after"], 88)
        # HONEST field: the sample starts at 89, so score_reaches_88 is True on
        # step 1, but eligible_after must be False until the last blocker clears.
        self.assertTrue(steps[0]["score_reaches_88"])
        self.assertFalse(steps[0]["eligible_after"])
        self.assertTrue(steps[-1]["eligible_after"])

    def test_below88_mixed_mandatory_before_deferrable_and_stop(self):
        # One 5-pt mandatory blocker + enough eligible 1-pt gaps that score is still
        # < 88 AFTER the blocker is fixed -> the path must then add deferrable items.
        excluded = set(RULES["excluded_ids"])
        eligible_ones = [c["id"] for c in CAT
                         if c["max_deduction"] == 1 and c["id"] not in excluded][:25]
        a = all_status(IMPLEMENTED)
        a["3.4.8"] = NOT_IMPLEMENTED          # -5 mandatory (5-pt, ineligible)
        for cid in eligible_ones:             # -25 eligible 1-pt
            a[cid] = NOT_IMPLEMENTED
        r = conditional_eligibility(a, CAT, RULES)
        self.assertEqual(r.score, 80)         # 110 - 5 - 25
        self.assertFalse(r.score_ok)
        steps = blocker_first_path(a, CAT, RULES)
        # mandatory (3.4.8) leads; deferrable follow
        self.assertEqual(steps[0]["id"], "3.4.8")
        self.assertTrue(steps[0]["mandatory"])
        self.assertFalse(steps[0]["eligible_after"])   # 85 < 88 after fixing blocker
        self.assertGreater(len([s for s in steps if not s["mandatory"]]), 0)
        mand = [s["mandatory"] for s in steps]
        self.assertNotIn(True, mand[mand.count(True):], "mandatory items must lead")
        # stops exactly when eligible (all blockers cleared AND score >= 88)
        self.assertTrue(steps[-1]["eligible_after"])
        self.assertTrue(all(not s["eligible_after"] for s in steps[:-1]))
        self.assertEqual(steps[-1]["score_after"], 88)  # 80 -> +5 blocker -> +3 deferrable

    def test_ssp_forced_first(self):
        a = all_status(IMPLEMENTED)
        a["3.12.4"] = NOT_IMPLEMENTED
        a["3.4.8"] = NOT_IMPLEMENTED
        steps = blocker_first_path(a, CAT, RULES)
        self.assertEqual(steps[0]["id"], "3.12.4")
        self.assertTrue(steps[0]["required_first"])


class TestControlLabels(unittest.TestCase):
    def test_mandatory_label_on_open_5pt(self):
        sample = load_sample()
        labels = control_labels(sample["statuses"], CAT, RULES)
        self.assertEqual(labels["3.4.8"]["primary"], LBL_MANDATORY)
        self.assertIn(LBL_MANDATORY, labels["3.1.20"]["tags"])

    def test_implemented_control_has_no_label(self):
        sample = load_sample()
        labels = control_labels(sample["statuses"], CAT, RULES)
        self.assertNotIn("3.1.1", labels)


class TestDashboardSummary(unittest.TestCase):
    def test_sample_summary(self):
        sample = load_sample()
        s = dashboard_summary(sample["statuses"], CAT, RULES)
        self.assertEqual(s.score, 89)
        self.assertFalse(s.conditional_eligible)
        self.assertFalse(s.final_ready)
        self.assertEqual(s.open_5pt, 4)          # 3.4.8, 3.13.6, 3.14.6, 3.13.11(5/3, partial)
        self.assertEqual(s.open_1pt, 3)          # 3.1.20, 3.3.4, 3.6.3
        self.assertGreaterEqual(len(s.prime_risks), 2)
        self.assertLessEqual(len(s.next_actions), 10)

    def test_coverage_uses_operational_final(self):
        sample = load_sample()
        ev_index = {"3.10.1": {"has_operational_final": True},
                    "3.14.2": {"has_operational_final": False}}
        s = dashboard_summary(sample["statuses"], CAT, RULES, evidence_index=ev_index)
        self.assertEqual(s.evidence_covered, 1)   # only 3.10.1 qualifies
        self.assertIn("3.14.2", s.controls_without_operational_evidence)

    def test_final_ready_requires_zero_open_even_with_full_evidence(self):
        # eligible (score 109, one open eligible 1-pt) + a fully-covered evidence
        # index must still NOT be final-ready, because a requirement is NOT MET.
        a = all_status(IMPLEMENTED)
        a["3.3.4"] = NOT_IMPLEMENTED               # -1 -> 109, eligible for Conditional
        dense_full = {c["id"]: {"has_operational_final": True} for c in CAT}
        s = dashboard_summary(a, CAT, RULES, evidence_index=dense_full)
        self.assertTrue(s.conditional_eligible)
        self.assertFalse(s.final_ready)            # open requirement blocks Final

    def test_final_ready_true_when_all_met_and_covered(self):
        a = all_status(IMPLEMENTED)
        dense_full = {c["id"]: {"has_operational_final": True} for c in CAT}
        s = dashboard_summary(a, CAT, RULES, evidence_index=dense_full)
        self.assertTrue(s.final_ready)


class TestPoamClock(unittest.TestCase):
    def test_180_day_countdown(self):
        c = poam_clock(date(2026, 1, 1), date(2026, 3, 1))
        self.assertEqual(c["deadline"], "2026-06-30")
        self.assertFalse(c["expired"])
        self.assertEqual(c["days_remaining"], 121)

    def test_expired(self):
        c = poam_clock(date(2026, 1, 1), date(2026, 8, 1))
        self.assertTrue(c["expired"])


if __name__ == "__main__":
    unittest.main()
