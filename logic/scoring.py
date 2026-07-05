"""SPRS scoring engine — NIST SP 800-171 DoD Assessment Methodology v1.2.1.

Pure functions, no Streamlit imports, fully unit-testable.

Status codes:
  implemented        no deduction
  not_implemented    deduct full weight (5 / 3 / 1); for 3.12.4 (SSP) the
                     methodology says the assessment cannot be completed
  partial_alt        ONLY 3.5.3 and 3.13.11 — deduct 3 instead of 5
                     (MFA for remote/privileged only; encryption not FIPS-validated)
  na_not_permitted   ONLY 3.1.12/3.1.13 (remote access), 3.1.16/3.1.17
                     (wireless), 3.1.18 (mobile) — no deduction when the
                     capability is not permitted at all (Annex A comments)
"""

from dataclasses import dataclass, field

IMPLEMENTED = "implemented"
NOT_IMPLEMENTED = "not_implemented"
PARTIAL_ALT = "partial_alt"
NA_NOT_PERMITTED = "na_not_permitted"

MAX_SCORE = 110
CONDITIONAL_THRESHOLD = 88  # CMMC L2 conditional-status minimum (0.8 x 110)


class InvalidStatus(ValueError):
    pass


def allowed_statuses(control: dict) -> list[str]:
    if control["special"] in ("mfa", "fips"):
        return [IMPLEMENTED, PARTIAL_ALT, NOT_IMPLEMENTED]
    if control["conditional_na"]:
        return [IMPLEMENTED, NOT_IMPLEMENTED, NA_NOT_PERMITTED]
    return [IMPLEMENTED, NOT_IMPLEMENTED]


def deduction_for(control: dict, status: str) -> int:
    if status not in allowed_statuses(control):
        raise InvalidStatus(f"{control['id']}: status '{status}' not allowed")
    if status in (IMPLEMENTED, NA_NOT_PERMITTED):
        return 0
    if status == PARTIAL_ALT:
        return 3
    return control["max_deduction"]  # not_implemented (0 for the NA-weight SSP)


@dataclass
class ScoreResult:
    score: int
    total_deducted: int
    implemented_count: int          # counts implemented + na_not_permitted
    open_count: int                 # any status that isn't fully implemented/NA
    ssp_missing: bool
    points_to_threshold: int
    per_control: dict = field(default_factory=dict)  # id -> deduction


def score_assessment(assessment: dict, catalog: list[dict]) -> ScoreResult:
    total = 0
    implemented = 0
    open_count = 0
    ssp_missing = False
    per_control = {}
    for c in catalog:
        status = assessment.get(c["id"], NOT_IMPLEMENTED)
        d = deduction_for(c, status)
        per_control[c["id"]] = d
        total += d
        if status in (IMPLEMENTED, NA_NOT_PERMITTED):
            implemented += 1
        else:
            open_count += 1
        if c["id"] == "3.12.4" and status != IMPLEMENTED:
            ssp_missing = True
    score = MAX_SCORE - total
    return ScoreResult(
        score=score,
        total_deducted=total,
        implemented_count=implemented,
        open_count=open_count,
        ssp_missing=ssp_missing,
        points_to_threshold=max(0, CONDITIONAL_THRESHOLD - score),
        per_control=per_control,
    )


def floor_score(catalog: list[dict]) -> int:
    return MAX_SCORE - sum(c["max_deduction"] for c in catalog)


def fastest_path(assessment: dict, catalog: list[dict],
                 target: int = CONDITIONAL_THRESHOLD) -> list[dict]:
    """Greedy order of open controls by points recovered (desc).

    Deductions are independent, so greedy-by-value is the optimal order by
    point count. Returns steps with running projected score. If the SSP is
    missing it is forced to step 1 regardless of point value, because no
    valid score exists without it.

    NOTE: the app uses readiness.blocker_first_path (which respects POA&M
    eligibility) for its "Blocker-First Readiness Path". This pure "fastest to 88"
    ordering is retained for reference and unit tests; it is intentionally NOT
    wired into the UI.
    """
    result = score_assessment(assessment, catalog)
    by_id = {c["id"]: c for c in catalog}
    open_ids = [cid for cid, d in result.per_control.items() if d > 0]
    ordered = sorted(open_ids, key=lambda cid: (-result.per_control[cid],
                                                _sort_key(cid)))
    if result.ssp_missing:
        ordered = ["3.12.4"] + [cid for cid in ordered if cid != "3.12.4"]
    steps, running = [], result.score
    for cid in ordered:
        gain = result.per_control.get(cid, 0)
        running += gain
        c = by_id[cid]
        steps.append({
            "id": cid,
            "short_title": c["short_title"],
            "gain": gain,
            "score_after": running,
            "reaches_target": running >= target,
            "required_first": cid == "3.12.4" and result.ssp_missing,
        })
        if running >= target and gain > 0:
            # keep listing? stop at target for a focused plan
            break
    return steps


def family_rollup(assessment: dict, catalog: list[dict]) -> list[dict]:
    rows = {}
    for c in catalog:
        fam = c["family"]
        r = rows.setdefault(fam, {
            "family": fam, "family_name": c["family_name"],
            "controls": 0, "implemented": 0,
            "points_possible": 0, "points_lost": 0,
        })
        status = assessment.get(c["id"], NOT_IMPLEMENTED)
        d = deduction_for(c, status)
        r["controls"] += 1
        r["points_possible"] += c["max_deduction"]
        r["points_lost"] += d
        if status in (IMPLEMENTED, NA_NOT_PERMITTED):
            r["implemented"] += 1
    out = []
    for r in rows.values():
        poss = r["points_possible"]
        r["points_kept"] = poss - r["points_lost"]
        r["pct_kept"] = 1.0 if poss == 0 else r["points_kept"] / poss
        out.append(r)
    return sorted(out, key=lambda r: _sort_key(r["family"] + ".0"))


def _sort_key(cid: str):
    return tuple(int(p) for p in cid.split("."))
