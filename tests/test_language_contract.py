"""Language-contract test — no user-facing string may imply a CMMC outcome the tool
cannot confer. See docs/language-contract.md.

Scans: app.py, disclosures.py, export/binder.py, README.md, docs/*.md, and the
rendered guidance text (plain/evidence/quick_win) in data/controls.json. Verbatim
NIST requirement text is authoritative source language and is out of scope.
"""

import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Terms that must never appear unless negated/disclaimed. Note: bare "compliant"/
# "compliance" is NOT here — it is legitimate product terminology ("compliant device",
# "compliance report"). What's forbidden is CLAIMING the user's status (phrases below).
FORBIDDEN = [
    "certified", "certification",
    "guaranteed", "audit-approved", "assessor-approved", "attestation",
    "cmmc level 2 package",
]
# Outcome-claim phrases — asserting the contractor passes / is compliant / is certified.
FORBIDDEN_PHRASES = [
    "you pass", "you will pass", "guaranteed to pass",
    "you are certified", "you're certified", "officially certified",
    "you are compliant", "you're compliant", "makes you compliant",
    "keeps you compliant", "keep you compliant", "stay compliant",
    "become compliant", "fully compliant", "now compliant", "is compliant",
]

NEGATION = re.compile(
    r"\b(not|no|never|isn'?t|aren'?t|cannot|can'?t|without|confers no|nothing)\b",
    re.IGNORECASE)

# Proper-noun contexts where a flagged word is part of an official name, not a claim.
# These are stripped before scanning so "...Model Certification (a DoD mark)" passes
# while a standalone "you'll be certified" claim still fails.
ALLOWED_CONTEXT = [
    "cybersecurity maturity model certification",  # the literal CMMC program name
]

# Exact user-facing lines that are known-good despite containing a flagged word.
ALLOWLIST = set()


def _lines_from(path: Path):
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        yield i, line


def _guidance_strings():
    payload = json.loads((ROOT / "data" / "controls.json").read_text(encoding="utf-8"))
    for c in payload["controls"]:
        g = c.get("guidance") or {}
        for key in ("plain", "evidence", "quick_win"):
            if g.get(key):
                yield f"controls.json:{c['id']}.{key}", g[key]


def _violations(label, text):
    low = text.lower()
    for phrase in ALLOWED_CONTEXT:            # strip official-name contexts first
        low = low.replace(phrase, " ")
    hits = []
    if NEGATION.search(text):
        return hits  # negation/disclaimer context is allowed for FORBIDDEN terms
    for term in FORBIDDEN:
        if term in low and text.strip() not in ALLOWLIST:
            hits.append((label, term, text.strip()[:120]))
    return hits


def _phrase_violations(label, text):
    low = text.lower()
    return [(label, p, text.strip()[:120]) for p in FORBIDDEN_PHRASES if p in low]


class TestLanguageContract(unittest.TestCase):
    def test_no_forbidden_claims(self):
        violations = []
        source_files = ["app.py", "disclosures.py", "export/binder.py", "README.md"]
        # docs/, EXCEPT the contract itself (it names the forbidden terms by design).
        source_files += [str(p.relative_to(ROOT)) for p in (ROOT / "docs").glob("*.md")
                         if p.name != "language-contract.md"]
        for rel in source_files:
            p = ROOT / rel
            for i, line in _lines_from(p):
                violations += _violations(f"{rel}:{i}", line)
                violations += _phrase_violations(f"{rel}:{i}", line)
        for label, text in _guidance_strings():
            violations += _violations(label, text)
            violations += _phrase_violations(label, text)
        msg = "\n".join(f"  {lbl}: {term!r} in: {snippet}" for lbl, term, snippet in violations)
        self.assertEqual(violations, [], f"\nForbidden language found:\n{msg}")


if __name__ == "__main__":
    unittest.main()
