"""CMMC Level 2 Conditional-status readiness engine.

The demo's scoring engine (logic/scoring.py) answers "what is the SPRS score?".
This module answers the question that actually decides eligibility:

    Reaching 88 (80%) is NECESSARY but NOT SUFFICIENT for Conditional status.

Per 32 CFR 170.21 a POA&M is permitted only if:
  1. score / 110 >= 0.8   (score >= 88), AND
  2. every open (NOT MET) requirement placed on the POA&M is worth <= 1 point,
     EXCEPT SC.L2-3.13.11 (CUI encryption) when encryption is employed but not
     FIPS-validated (the -3 partial), which MAY be POA&M'd, AND
  3. none of six named 1-point requirements are open:
     AC.L2-3.1.20, AC.L2-3.1.22, CA.L2-3.12.4 (SSP), PE.L2-3.10.3/4/5.

So a contractor can sit at exactly 89 and still be ineligible. This module makes
that compound gate first-class. It is PURE: no Streamlit, no I/O; `today` is a
parameter. Rules are injected as a plain dict (see data/poam_eligibility.json).
"""

from dataclasses import dataclass, field
from datetime import date, timedelta

from logic.scoring import (
    IMPLEMENTED, NA_NOT_PERMITTED, NOT_IMPLEMENTED,
    CONDITIONAL_THRESHOLD,
    deduction_for, score_assessment,
)

# Label vocabulary (the five readiness labels the UI renders).
LBL_MANDATORY = "Cannot be deferred to a POA&M"
LBL_HIGH_IMPACT = "Highest score impact"
LBL_PRIORITY = "Likely remediation priority"
LBL_NEEDS_REVIEW = "POA&M eligibility needs review"
LBL_NOT_FINAL = "Not sufficient for final readiness"
LBL_SSP_BLOCKER = "SSP/evidence blocker"


def _is_open(control: dict, status: str) -> bool:
    return status not in (IMPLEMENTED, NA_NOT_PERMITTED)


def evidence_index_from_register(register: dict) -> dict:
    """Distil an evidence REGISTER (control_id -> [entries]) into the plain index the
    engine consumes: control_id -> {'has_operational_final': bool, 'entries': int}.
    A control counts as covered ONLY when an entry is document-final AND demonstrates
    operation AND reviewed — a signed-but-not-operational document does not count.
    Shared by the UI and the binder so the two never disagree."""
    idx = {}
    for cid, entries in (register or {}).items():
        covered = any(
            isinstance(e, dict)
            and e.get("doc_status") == "final"
            and e.get("impl_status") == "demonstrates_operation"
            and e.get("review_status") == "reviewed"
            for e in entries
        )
        idx[cid] = {"has_operational_final": covered, "entries": len(entries)}
    return idx


def poam_eligible(control: dict, status: str, rules: dict) -> bool:
    """Can this control, in this status, be placed on a POA&M for Conditional status?

    Eligibility is STATUS-dependent, not id-only: 3.13.11 is eligible at the -3
    partial but NOT at the -5 not-implemented.
    """
    cid = control["id"]
    if cid in set(rules.get("excluded_ids", [])):
        return False
    exc = rules.get("exceptions", {}).get(cid)
    if exc is not None and status == exc.get("allowed_status"):
        return True
    return deduction_for(control, status) <= rules.get("max_points", 1)


@dataclass
class EligibilityResult:
    score: int
    score_ok: bool          # score >= conditional_min
    ssp_ok: bool            # SSP (3.12.4) present
    eligible: bool          # the full compound gate
    blocking_ids: list = field(default_factory=list)   # open + NOT poam-eligible
    reasons: list = field(default_factory=list)         # human-readable


def conditional_eligibility(assessment: dict, catalog: list, rules: dict) -> EligibilityResult:
    """The compound Conditional-status gate (32 CFR 170.21)."""
    by_id = {c["id"]: c for c in catalog}
    result = score_assessment(assessment, catalog)
    threshold = rules.get("conditional_min", CONDITIONAL_THRESHOLD)
    score_ok = result.score >= threshold
    ssp_ok = not result.ssp_missing

    blocking = []
    for cid, c in by_id.items():
        status = assessment.get(cid, NOT_IMPLEMENTED)
        if _is_open(c, status) and not poam_eligible(c, status, rules):
            blocking.append(cid)
    blocking.sort(key=_sort_key)

    reasons = []
    if not score_ok:
        reasons.append(f"Score {result.score} is below the {threshold}-point minimum.")
    if not ssp_ok:
        reasons.append("No System Security Plan (3.12.4) — no valid assessment exists.")
    if blocking:
        reasons.append(
            f"{len(blocking)} open requirement(s) cannot be deferred to a POA&M "
            "and must be MET at assessment: " + ", ".join(blocking) + "."
        )

    eligible = score_ok and ssp_ok and not blocking
    return EligibilityResult(
        score=result.score, score_ok=score_ok, ssp_ok=ssp_ok,
        eligible=eligible, blocking_ids=blocking, reasons=reasons,
    )


def blocker_first_path(assessment: dict, catalog: list, rules: dict,
                       target: "int | None" = None) -> list:
    """Ordered remediation plan that respects POA&M eligibility.

    SSP first (if missing) -> ALL POA&M-ineligible open items (mandatory; they can
    never be deferred), highest-points first -> then eligible open items by points
    until score >= target. Typically OVERSHOOTS the raw 88 threshold, because every
    ineligible item must be met regardless of point math. That overshoot is the
    honest answer the demo exists to show.
    """
    if target is None:
        target = rules.get("conditional_min", CONDITIONAL_THRESHOLD)
    by_id = {c["id"]: c for c in catalog}
    result = score_assessment(assessment, catalog)

    open_items = []
    for cid, c in by_id.items():
        status = assessment.get(cid, NOT_IMPLEMENTED)
        if _is_open(c, status):
            open_items.append((cid, deduction_for(c, status),
                               poam_eligible(c, status, rules)))

    ssp_missing = result.ssp_missing
    mandatory = sorted(
        [(cid, d) for cid, d, elig in open_items if not elig and cid != "3.12.4"],
        key=lambda x: (-x[1], _sort_key(x[0])))
    deferrable = sorted(
        [(cid, d) for cid, d, elig in open_items if elig],
        key=lambda x: (-x[1], _sort_key(x[0])))

    mandatory_total = (1 if ssp_missing else 0) + len(mandatory)
    steps, running, mandatory_done = [], result.score, 0

    def add(cid, gain, mandatory_flag, required_first=False):
        nonlocal running, mandatory_done
        running += gain
        if mandatory_flag:
            mandatory_done += 1
        steps.append({
            "id": cid, "short_title": by_id[cid]["short_title"],
            "gain": gain, "score_after": running,
            "mandatory": mandatory_flag, "required_first": required_first,
            # HONEST fields: score crossing 88 is NOT eligibility. `eligible_after`
            # is only True once every mandatory blocker is cleared AND score >= 88.
            "score_reaches_88": running >= target,
            "eligible_after": mandatory_done == mandatory_total and running >= target,
        })

    if ssp_missing:
        add("3.12.4", 0, True, required_first=True)
    for cid, d in mandatory:
        add(cid, d, True)               # must be met no matter what
    for cid, d in deferrable:
        if mandatory_done == mandatory_total and running >= target:
            break
        add(cid, d, False)
    return steps


def control_labels(assessment: dict, catalog: list, rules: dict,
                   evidence_index: dict = None) -> dict:
    """Per-open-control readiness labels for the UI. `evidence_index` optional
    (maps control_id -> {'has_operational_final': bool}); when absent, evidence
    labels are simply omitted."""
    evidence_index = evidence_index or {}
    by_id = {c["id"]: c for c in catalog}
    result = score_assessment(assessment, catalog)
    out = {}
    for cid, c in by_id.items():
        status = assessment.get(cid, NOT_IMPLEMENTED)
        tags = []
        d = result.per_control.get(cid, 0)
        if _is_open(c, status):
            if not poam_eligible(c, status, rules):
                tags.append(LBL_MANDATORY)
            else:
                tags.append(LBL_NOT_FINAL)   # deferrable for Conditional, still blocks Final
            if d >= 5:
                tags.append(LBL_HIGH_IMPACT)
            if cid == "3.12.4" and result.ssp_missing:
                tags.append(LBL_SSP_BLOCKER)
        elif status != NA_NOT_PERMITTED:
            # in-scope + implemented, but evidence not demonstrably operational -> Final blocker.
            # (na_not_permitted is out of scope; never an evidence blocker.)
            ev = evidence_index.get(cid)
            if ev is not None and not ev.get("has_operational_final", False):
                tags.append(LBL_SSP_BLOCKER)
        if tags:
            out[cid] = {"primary": tags[0], "tags": tags}
    return out


@dataclass
class DashboardSummary:
    score: int
    ssp_missing: bool
    conditional_eligible: bool
    final_ready: bool
    open_5pt: int
    open_3pt: int
    open_1pt: int
    blocking_ids: list = field(default_factory=list)
    evidence_applicable: int = 0
    evidence_covered: int = 0
    controls_without_operational_evidence: list = field(default_factory=list)
    next_actions: list = field(default_factory=list)
    prime_risks: list = field(default_factory=list)
    reasons: list = field(default_factory=list)

    @property
    def coverage_pct(self) -> float:
        return 0.0 if self.evidence_applicable == 0 else self.evidence_covered / self.evidence_applicable


def dashboard_summary(assessment: dict, catalog: list, rules: dict,
                      evidence_index: dict = None, today: date = None) -> DashboardSummary:
    """One pure summary for the VP dashboard AND the binder exec summary (single
    source of truth, no drift).

    `evidence_index` maps control_id -> {'has_operational_final': bool}. Callers
    should pass a DENSE index over applicable controls (a missing entry counts as
    uncovered here, and produces no label in control_labels — pass both the same
    index so the two screens agree). `today` reserved for date-based risks."""
    evidence_index = evidence_index or {}
    by_id = {c["id"]: c for c in catalog}
    elig = conditional_eligibility(assessment, catalog, rules)

    open_5 = open_3 = open_1 = open_count = 0
    applicable = []            # in-scope controls (excludes scope-earned N/A)
    without_ev = []
    for cid, c in by_id.items():
        status = assessment.get(cid, NOT_IMPLEMENTED)
        if status != NA_NOT_PERMITTED:
            applicable.append(cid)
        if _is_open(c, status):
            open_count += 1     # incl. an open SSP (max_deduction 0, no weight bucket)
            w = c["max_deduction"]
            if w == 5:
                open_5 += 1
            elif w == 3:
                open_3 += 1
            elif w == 1:
                open_1 += 1
        # a control lacking demonstrably-operational, reviewed, final evidence
        ev = evidence_index.get(cid)
        if status != NA_NOT_PERMITTED and (ev is None or not ev.get("has_operational_final", False)):
            without_ev.append(cid)

    covered = sum(1 for cid in applicable
                  if evidence_index.get(cid, {}).get("has_operational_final", False))

    next_actions = blocker_first_path(assessment, catalog, rules)[:10]

    # Final status requires ALL requirements MET (not merely POA&M-eligible) AND
    # every in-scope control backed by demonstrably-operational, reviewed evidence.
    final_ready = (elig.eligible and open_count == 0 and not without_ev)

    risks = []
    if elig.ssp_ok is False:
        risks.append("No System Security Plan (3.12.4) — no valid assessment exists.")
    if elig.blocking_ids:
        risks.append(f"{len(elig.blocking_ids)} open requirement(s) cannot be deferred "
                     "to a POA&M and block Conditional status.")
    if open_5:
        risks.append(f"{open_5} open 5-point requirement(s) (POA&M-ineligible unless "
                     "3.13.11 encryption at the −3 partial).")
    if without_ev:
        risks.append(f"{len(without_ev)} in-scope control(s) lack demonstrably operational, "
                     "reviewed evidence.")

    return DashboardSummary(
        score=elig.score, ssp_missing=not elig.ssp_ok,
        conditional_eligible=elig.eligible, final_ready=final_ready,
        open_5pt=open_5, open_3pt=open_3, open_1pt=open_1,
        blocking_ids=elig.blocking_ids,
        evidence_applicable=len(applicable), evidence_covered=covered,
        controls_without_operational_evidence=sorted(without_ev, key=_sort_key),
        next_actions=next_actions, prime_risks=risks, reasons=elig.reasons,
    )


def poam_clock(conditional_date: date, today: date, closeout_days: int = 180) -> dict:
    """180-day Conditional->Final countdown, anchored ONLY to a user-entered actual
    assessment/Conditional date. Never projected from the tool's own numbers."""
    deadline = conditional_date + timedelta(days=closeout_days)
    days_remaining = (deadline - today).days
    return {
        "deadline": deadline.isoformat(),
        "days_remaining": days_remaining,
        "expired": days_remaining < 0,
    }


def _sort_key(cid: str):
    return tuple(int(p) for p in cid.split("."))
