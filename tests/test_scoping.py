"""Tests for logic/scoping.py — scope-earned N/A and reconciliation."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from logic.catalog import controls, load_sample
from logic.scoring import IMPLEMENTED, NA_NOT_PERMITTED, NOT_IMPLEMENTED, score_assessment
from logic.scoping import (
    ASSET_CATEGORIES, conditional_na_applicable, reconcile_na_statuses,
)

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


class TestSampleScope(unittest.TestCase):
    """The flagship sample must showcase scope + an asset inventory (and doing so must
    not shift the 89 score)."""

    def setUp(self):
        self.sample = load_sample()

    def test_sample_has_confirmed_scope(self):
        scope = self.sample.get("scope", {})
        self.assertTrue(scope.get("confirmed_at"))
        for cap in ("handles_cui", "remote_access_permitted",
                    "wireless_permitted", "mobile_permitted"):
            self.assertIs(scope.get(cap), True)

    def test_sample_scope_earns_no_na_and_keeps_89(self):
        scope = self.sample["scope"]
        self.assertEqual(conditional_na_applicable(scope, CAT), set())
        self.assertEqual(score_assessment(self.sample["statuses"], CAT).score, 89)

    def test_sample_has_valid_asset_inventory(self):
        assets = self.sample.get("scope_assets", [])
        self.assertGreaterEqual(len(assets), 5)
        for a in assets:
            self.assertTrue(a.get("name"))
            self.assertIn(a.get("category"), ASSET_CATEGORIES)
        self.assertGreaterEqual(len({a["category"] for a in assets}), 3)


if __name__ == "__main__":
    unittest.main()
