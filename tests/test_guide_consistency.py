"""Guide-consistency test — the Survival Guide's control tables must agree with the
app's ruleset. The guide (docs/guide-src/survival-guide.html, published as
docs/CMMC_Level_2_Survival_Guide.pdf) restates all 110 requirements with their SPRS
point values and POA&M-eligibility flags; this test asserts every row against
data/controls.json and data/poam_eligibility.json, so the app and the guide can never
tell a reader two different stories about the same rule.
"""

import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

GUIDE_HTML = ROOT / "docs" / "guide-src" / "survival-guide.html"

ROW_ID = re.compile(r'<td class="id">(3\.\d+\.\d+)</td>')
ROW_PTS = re.compile(r'<span class="pts (p\w)">([^<]+)</span>')


def _guide_rows():
    """Parse each control row of the guide's family tables independently.

    Returns {control_id: {"pts": text, "poam": "never" | "ok" | "no"}}.
    """
    html = GUIDE_HTML.read_text(encoding="utf-8")
    rows = {}
    for tr in re.findall(r"<tr>(.*?)</tr>", html, re.S):
        id_match = ROW_ID.search(tr)
        if not id_match:
            continue
        cid = id_match.group(1)
        pts_match = ROW_PTS.search(tr)
        if 'class="never"' in tr:
            poam = "never"
        elif 'class="ok-poam"' in tr:
            poam = "ok"
        elif 'class="no-poam"' in tr:
            poam = "no"
        else:
            poam = None
        assert cid not in rows, f"duplicate guide row for {cid}"
        rows[cid] = {"pts": pts_match.group(2) if pts_match else None, "poam": poam}
    return rows


class TestGuideConsistency(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.guide = _guide_rows()
        payload = json.loads((ROOT / "data" / "controls.json").read_text(encoding="utf-8"))
        cls.controls = {c["id"]: c for c in payload["controls"]}
        cls.elig = json.loads(
            (ROOT / "data" / "poam_eligibility.json").read_text(encoding="utf-8"))

    def test_guide_covers_exactly_the_110_controls(self):
        self.assertEqual(set(self.guide), set(self.controls))

    def test_point_values_match_catalog_weights(self):
        mismatches = []
        for cid, row in sorted(self.guide.items()):
            weight = self.controls[cid]["weight"]
            expected = {"5/3": "3/5", "NA": "SSP"}.get(weight, str(weight))
            if row["pts"] != expected:
                mismatches.append(f"{cid}: guide shows {row['pts']!r}, catalog weight is {weight!r}")
        self.assertEqual(mismatches, [], "\n".join(mismatches))

    def test_poam_flags_match_eligibility_ruleset(self):
        excluded = set(self.elig["excluded_ids"])
        exceptions = set(self.elig["exceptions"])
        max_points = self.elig["max_points"]
        mismatches = []
        for cid, row in sorted(self.guide.items()):
            weight = self.controls[cid]["weight"]
            if cid in excluded:
                expected = "never"
            elif cid in exceptions:
                expected = "ok"  # 3.13.11: only the partial (-3) case may be POA&M'd
            elif isinstance(weight, int) and weight <= max_points:
                expected = "ok"
            else:
                expected = "no"  # includes the 5/3 partial without an exception (3.5.3)
            if row["poam"] != expected:
                mismatches.append(f"{cid}: guide shows {row['poam']!r}, ruleset expects {expected!r}")
        self.assertEqual(mismatches, [], "\n".join(mismatches))


if __name__ == "__main__":
    unittest.main()
