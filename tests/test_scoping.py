"""Tests for logic/scoping.py — scope-earned N/A and reconciliation."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from logic.catalog import controls
from logic.scoring import IMPLEMENTED, NA_NOT_PERMITTED, NOT_IMPLEMENTED
from logic.scoping import conditional_na_applicable, reconcile_na_statuses

CAT = controls()

ALL_PERMITTED = {
    "handles_cui": True, "remote_access_permitted": True,
    "wireless_permitted": True, "mobile_permitted": True,
    "confirmed_at": "2026-07-04",
}


def scope(**over):
    s = dict(ALL_PERMITTED)
    s.update(over)
    return s


class TestConditionalNaApplicable(unittest.TestCase):
    def test_unconfirmed_scope_offers_no_na(self):
        s = scope(confirmed_at=None, wireless_permitted=False)
        self.assertEqual(conditional_na_applicable(s, CAT), set())

    def test_all_permitted_offers_no_na(self):
        self.assertEqual(conditional_na_applicable(scope(), CAT), set())

    def test_wireless_not_permitted_enables_wireless_controls(self):
        s = scope(wireless_permitted=False)
        self.assertEqual(conditional_na_applicable(s, CAT), {"3.1.16", "3.1.17"})

    def test_remote_and_mobile(self):
        s = scope(remote_access_permitted=False, mobile_permitted=False)
        self.assertEqual(conditional_na_applicable(s, CAT), {"3.1.12", "3.1.13", "3.1.18"})


class TestReconcile(unittest.TestCase):
    def test_invalid_na_is_reset(self):
        # wireless is permitted, but 3.1.16 was left N/A -> must reset
        a = {c["id"]: IMPLEMENTED for c in CAT}
        a["3.1.16"] = NA_NOT_PERMITTED
        new, reset = reconcile_na_statuses(a, scope(), CAT)
        self.assertEqual(reset, ["3.1.16"])
        self.assertEqual(new["3.1.16"], NOT_IMPLEMENTED)

    def test_valid_na_is_kept(self):
        s = scope(wireless_permitted=False)
        a = {c["id"]: IMPLEMENTED for c in CAT}
        a["3.1.16"] = NA_NOT_PERMITTED
        new, reset = reconcile_na_statuses(a, s, CAT)
        self.assertEqual(reset, [])
        self.assertEqual(new["3.1.16"], NA_NOT_PERMITTED)


if __name__ == "__main__":
    unittest.main()
