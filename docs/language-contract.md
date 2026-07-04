# Language contract

This tool guides real defense-contractor readiness conversations, so its wording is
held to a contract and enforced by a test (`tests/test_language_contract.py`). The
tool produces a **self-estimate** and **confers no CMMC status** — the language must
never imply otherwise.

## Forbidden (imply a third-party outcome the tool can't produce)

Never assert, in any user-facing string, that a user *is* or *will be*:

- **certified / certification** (except as a disclaimer: "not a certification")
- **claiming compliance status** — phrases like "you are compliant", "makes you
  compliant", "fully compliant", "now compliant", "is compliant". (The bare adjective
  is fine in product terminology: an Intune "compliant device", a "compliance report".)
- **passing / you pass / guaranteed to pass**
- **audit-approved / assessor-approved**
- **attestation** as something the tool completes (except negated)
- **"CMMC Level 2 Package"** (mirrors the official C3PAO submission)

## Approved vocabulary

- "projected readiness", "self-estimate", "self-reported"
- "prep" / "Assessment Prep Binder"
- "not conditionally ready", "Conditional-eligible" (with the self-estimate qualifier)
- "blocker-first", "cannot be deferred to a POA&M"
- "confers no CMMC status"

## How the test works

It scans user-facing strings (the UI source, `disclosures.py`, the binder, README,
`docs/`, and the rendered guidance text in `data/controls.json`). A forbidden term
fails the build **unless** it appears in a negation/disclaimer context (e.g. "not a
certification"), inside an official proper-noun name (the program name "Cybersecurity
Maturity Model Certification" is exempt), or on an explicit allowlist. Requirement text
quoted verbatim from NIST SP 800-171 is authoritative source language and is out of scope.
