"""Shared honesty/transparency content — single source for the UI, the binder, and
the language-contract test. Keeping these strings here prevents drift between what
the screen says and what the exported document says.

Everything here is deliberately worded to the approved language contract: the tool
produces a SELF-ESTIMATE and confers no CMMC status.
"""

# What the app shows  ->  the official CMMC meaning  ->  how it is actually earned.
# The app confers NONE of these; it only projects readiness from self-reported input.
APP_TO_CMMC_STATUS = [
    ("Not conditionally ready",
     "— (no CMMC status)",
     "Close the blockers first; a self-estimate, not a status."),
    ("Projected: Conditional-eligible",
     "Conditional CMMC Status",
     "Earned only by an assessment with a compliant POA&M recorded in SPRS."),
    ("Projected: Final-ready",
     "Final CMMC Status",
     "Earned only when all requirements are met and affirmed in SPRS "
     "(C3PAO assessment where required)."),
]

# One-line qualifier shown wherever a readiness verdict appears.
READINESS_QUALIFIER = (
    "Projected readiness is a self-estimate. A CMMC Status is conferred only by an "
    "assessment recorded in SPRS — this tool confers none."
)

# The standing disclaimer (a disclaimer, not a claim — the language-contract test
# must treat these negated statements as allowed).
DISCLAIMER = (
    "This workspace is a self-assessment aid and a readiness self-estimate. It is "
    "not a certification, not legal advice, not a C3PAO assessment, and not a "
    "substitute for the official NIST SP 800-171 DoD Assessment Methodology or "
    "32 CFR Part 170. It confers no CMMC status. Verify results against the official "
    "sources before posting any score to SPRS."
)

# Data boundary + operating posture, shown in the Transparency panel and the
# evidence step. Drawn precisely because the tool's purpose IS entering gap data.
DATA_BOUNDARY = (
    "**Do not enter real CUI, credentials, IP addresses, hostnames, system "
    "identifiers, or network details in any field.** Expected input: control "
    "statuses, scope answers, generic evidence titles, and where evidence *lives* "
    "(a pointer, not the file). Nothing is stored on a server — this session lives "
    "in your browser only; export before closing the tab."
)

OPERATING_POSTURE = (
    "Run real-contractor sessions locally (`streamlit run app.py`). Any public or "
    "shared URL should serve the sample only — never a real organization's session."
)

# The five readiness labels (mirrors logic.readiness) for UI legend rendering.
LABEL_HELP = {
    "Cannot be deferred to a POA&M":
        "This open requirement is NOT POA&M-eligible under 32 CFR 170.21 — it must "
        "be MET at assessment. It blocks Conditional status regardless of score.",
    "Not sufficient for final readiness":
        "POA&M-eligible for Conditional status, but still open — it must be met and "
        "closed out for Final status.",
    "Highest score impact": "A 5-point requirement — the largest single score move.",
    "SSP/evidence blocker":
        "Either the System Security Plan is missing (no valid assessment exists) or "
        "this control lacks demonstrably operational, reviewed evidence.",
}
