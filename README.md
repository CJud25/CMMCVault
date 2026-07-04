# 🛡️ CMMC Vault — CMMC Level 2 readiness "Super Demo"

A **session-only** Streamlit workspace that turns a NIST SP 800-171 / SPRS scoring
demo into a **guided readiness conversation tool for small defense contractors.**
Its whole reason to exist is one truth most spreadsheets miss:

> **Reaching 88 (80%) is necessary but *not sufficient* for CMMC Conditional
> status.** Eligibility is a *compound gate* under 32 CFR 170.21.

**Session-only. No accounts, no database, nothing stored on a server.** Every visitor
starts fresh; *Load sample* seeds a shop that scores **89 and is still not
conditionally ready.** Export your work to JSON before closing the tab, and re-import
to resume.

---

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Real-contractor sessions should be run **locally**. Any public/shared URL should
serve the sample only — never a real organization's session.

## The 60-second demo script — the 89-that-isn't-ready

1. Sidebar → **Load sample**. "A 28-person machine shop that thinks it's basically there."
2. **Dashboard**: **Score 89 — Not conditionally ready.** "They're *above* the 88-point
   floor — and still ineligible. Watch why."
3. The **blockers**: three open 5-point controls (3.4.8, 3.13.6, 3.14.6) and one
   1-pointer (3.1.20) that **cannot be placed on a POA&M** under 32 CFR 170.21. "Score
   gets you in the room; these get you eligible."
4. **Blocker-First Readiness Path** tab: mandatory (non-deferrable) items first — the
   plan *overshoots* 88, because you can't defer these no matter the point math.
5. **Scope** tab: define the boundary first — that's what earns the right to mark a
   control "N/A." **Evidence** tab: know *what* you need, *where* it lives, *who* owns
   it, and whether it's document-final, operational, and reviewed.
6. Sidebar → **Assessment Prep Binder (.docx)**: "What you bring *to* an assessment —
   the control matrix, POA&M with eligibility flags, and an evidence index."

## Why 88 is not enough (the compound gate — 32 CFR 170.21)

A POA&M is permitted only if **every** open requirement on it is POA&M-eligible:

- Requirements worth **more than 1 point are not POA&M-eligible** — except **3.13.11**
  (CUI encryption) at the −3 partial (encryption in use, not FIPS-validated).
- Six 1-point requirements are **never** POA&M-eligible: **3.1.20, 3.1.22, 3.12.4
  (SSP), 3.10.3, 3.10.4, 3.10.5**.
- POA&M items must be closed within **180 days** of the Conditional status date.

The ruleset lives in `data/poam_eligibility.json` and is asserted on every build.

## Data provenance & accuracy

- Control weights transcribed from the *NIST SP 800-171 DoD Assessment Methodology,
  v1.2.1 (2020-06-24), Annex A*; POA&M rules from *32 CFR 170.21*.
- `scripts/build_catalog.py --check` hard-asserts the published weight distribution
  (44×5pt, 14×3pt, 51×1pt, 1 NA; floor −203), the eligibility ruleset, and **that the
  sample scores exactly 89 and is not conditionally ready** — so neither the data nor
  the centerpiece can silently drift.
- Plain-English guidance marked *draft* is not yet expert-reviewed (the UI badges it).
- **Before using with a real contractor:** spot-check `data/controls.json` against the
  official PDF and run `python scripts/build_catalog.py --check`.

## Tests

```bash
python -m unittest discover tests -v   # scoring, readiness, scoping, binder, import
```

## What this is not

Not a certification, not legal advice, not a C3PAO assessment. It confers no CMMC
status and stores nothing. **Do not enter real CUI, credentials, IP addresses,
hostnames, or system identifiers** — use generic names and location pointers.

## Deliberately out of scope (frozen)

Accounts/auth, server-side persistence, real evidence file storage, and any
multi-tenant SaaS are **frozen** — not built until this session-only tool proves value
*and* a security review is completed. See the plan's *Phase 2 (FROZEN)* appendix.

## Disclaimer

Self-assessment aid and readiness self-estimate only — not a certification, not legal
advice, not a substitute for the official DoD Assessment Methodology or 32 CFR Part
170. A CMMC Status is conferred only by an assessment recorded in SPRS. Verify results
against official sources before posting any score.
