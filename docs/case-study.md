# CMMC Vault — Case Study

## Problem

The Department of Defense scores a contractor's NIST SP 800-171 self-assessment on a
scale that starts at 110 and subtracts 5, 3, or 1 points for each unmet requirement.
Most self-assessment spreadsheets stop at that number and treat 88 —
eighty percent of 110 — as the finish line for CMMC Level 2. It is not. Under
32 CFR 170.21, "Conditional" eligibility is a *compound* gate: the score must clear 88,
every open requirement deferred to a Plan of Action and Milestones (POA&M) must be
low-value enough to defer, and a specific handful of requirements can never be deferred
at all. A contractor can sit above the threshold and still be ineligible, and a
score-only spreadsheet never explains why. CMMC Vault makes that gap impossible to miss
and turns it into an ordered plan of work.

## Stakeholders

The primary user is the person at a small defense contractor — often a roughly
25-person machine shop — who owns readiness without a dedicated security team.
Leadership needs a defensible read on whether the company can win or keep work involving
Controlled Unclassified Information. Primes and customers need confidence that a
subcontractor is not about to fail an assessment, and a C3PAO (the third-party assessor)
benefits when a contractor arrives organized. The tool speaks to all four while stating
plainly what it is: a self-assessment aid and readiness self-estimate that confers no
CMMC status.

## Data

Three data files drive the engine. `data/controls.json` is the built catalog of all
110 requirements with their point weights and plain-English guidance.
`data/poam_eligibility.json` encodes the 32 CFR 170.21 POA&M ruleset — the score
threshold and the never-deferrable requirements — as a single source of truth.
`data/sample_assessment.json` is a fictional example organization for demonstration and
testing. The framework encoded is NIST SP 800-171 Revision 2 (requirement text), the
DoD Assessment Methodology weighting (the 5/3/1 points and score range), NIST
SP 800-171A (the assessment objectives), and 32 CFR 170.21 (the compound eligibility
gate).

## Method

The design keeps a small, pure logic core free of any UI framework: `scoring.py` (the
SPRS point engine), `readiness.py` (the compound eligibility gate, the blocker-first
remediation path, and the 180-day Conditional-to-Final clock), `scoping.py` (which
controls a defined boundary earns the right to mark "N/A"), and `catalog.py` (loads the
built catalog and rulesets). A Streamlit app renders that core but holds no business
logic itself, so the screen and the exported binder can never disagree. A build script
assembles and validates the catalog and runs in CI with a `--check` flag that re-asserts
the entire ruleset on every build, so neither the data nor the teaching example can
silently drift.

## Validation

The suite runs 63 tests and passes two independent ways: with `pytest` (`63 passed`)
and on the no-extra-dependencies path (`python -m unittest discover tests` —
`Ran 63 tests ... OK`). Coverage of the pure-logic package is 98% (281 statements, 6
missed): `scoping.py` and `scoring.py` at 100%, `readiness.py` at 97%, and `catalog.py`
at 94%. The catalog integrity check (`scripts/build_catalog.py --check`) exits 0 and
asserts the weight distribution — 44 five-point, 14 three-point, and 51 one-point
requirements plus 1 non-scored System Security Plan — a score floor of −203, all 110
guidance entries SME-reviewed, and 6 controls that can never go on a POA&M. Linting is
clean (ruff); CI runs ruff, pytest, and the catalog check on Python 3.11; and the
Streamlit app boots headless (HTTP 200). As an adversarial cross-check, a red-team
skeptic recomputed the sample score from the raw weights and statuses in the data
files — bypassing the app's scoring code — and reproduced it exactly.

## Impact

### Measured (from this run)

- 63 tests pass; 98% coverage of the pure-logic package (281 statements, 6 missed),
  with `scoping.py` and `scoring.py` fully covered.
- ruff clean; CI green on Python 3.11 across ruff, pytest, and the catalog integrity
  check; the app boots headless with HTTP 200.
- The catalog check passes (exit 0): 44 / 14 / 51 weighted requirements plus one
  non-scored System Security Plan, a −203 score floor, 110 SME-reviewed guidance
  entries, and 6 never-deferrable controls encoded.

### Illustrative (synthetic / demo)

- The bundled sample is a fictional machine shop, "Gulf Coast Precision Machining"
  (7 assets). It scores exactly 89 — above the 88 floor — yet the tool reports it
  **not conditionally ready** (eligible = false), because four requirements
  (3.1.20, 3.4.8, 3.13.6, 3.14.6) are open and cannot all be deferred to a POA&M.
- This is the centerpiece teaching point, produced on fictional data: clearing 88 gets
  you in the room; clearing these specific blockers gets you eligible. The output is a
  readiness self-estimate and confers no CMMC status.

## Limitations

The tool relies on self-reported input and verifies nothing about the actual
environment. Requirement weights are transcribed from the DoD methodology and should be
spot-checked against the official PDF before high-stakes use. The plain-English guidance
was drafted with AI assistance and reviewed in a source-checked editorial pass — not a
sign-off by a licensed CMMC professional or a C3PAO — so it is advisory. Evidence is
tracked at the control level; the finer 320-objective level of NIST SP 800-171A is not
yet modeled. There is no persistence beyond manual JSON export and import, and the
encoded regulations are pinned rather than auto-updated, so any result should be treated
as potentially stale until the source versions are re-confirmed.

## Next Build

The clearest next steps are to model NIST SP 800-171A at the 320-objective granularity
so evidence maps to what an assessor actually tests; to add a source-reconciliation pass
that flags when a pinned regulation may have been superseded; and to commission the
dedicated security review that gates any move beyond the current session-only design
toward accounts, server-side persistence, or a hosted multi-tenant offering — each
deliberately frozen until the tool has proven its value.
