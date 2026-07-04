"""Assessment scope -> which controls may legally be marked N/A.

The demo let a user mark 3.1.12/13/16/17/18 as "N/A — capability not permitted"
UNCONDITIONALLY, which silently inflates the score (mark wireless N/A while using
wireless). Under the DoD methodology those five carry no deduction only when the
capability is genuinely not permitted at all. This module derives that permission
from the scope answers, so the UI can offer N/A only when the scope earns it.

Pure: no Streamlit, no I/O. `scope` is a plain dict.
"""

from logic.scoring import NA_NOT_PERMITTED, NOT_IMPLEMENTED

# The five conditional-N/A controls and the scope capability each depends on.
# N/A is permitted only when that capability is NOT permitted in scope.
_CAPABILITY_CONTROLS = {
    "remote_access_permitted": ("3.1.12", "3.1.13"),
    "wireless_permitted": ("3.1.16", "3.1.17"),
    "mobile_permitted": ("3.1.18",),
}

# Categories from the CMMC Level 2 Scoping Guide (32 CFR 170.19).
ASSET_CATEGORIES = [
    "CUI Asset",
    "Security Protection Asset",
    "Contractor Risk Managed Asset",
    "Specialized Asset",
    "Out-of-Scope Asset",
]


def conditional_na_applicable(scope: dict, catalog: list = None) -> set:
    """Set of control ids for which `na_not_permitted` is a LEGAL choice, given the
    scope answers. Empty until the scope is confirmed — you cannot claim a
    capability is out of scope before you have defined scope."""
    if not scope.get("confirmed_at"):
        return set()
    applicable = set()
    for capability, cids in _CAPABILITY_CONTROLS.items():
        # capability permitted -> N/A NOT allowed; not permitted -> N/A allowed
        if not scope.get(capability, True):
            applicable.update(cids)
    if catalog is not None:
        valid = {c["id"] for c in catalog if c.get("conditional_na")}
        applicable &= valid
    return applicable


def reconcile_na_statuses(assessment: dict, scope: dict, catalog: list) -> tuple:
    """Reset any saved `na_not_permitted` status that scope no longer earns.

    Returns (new_assessment, reset_ids). Called after scope changes so a control
    marked N/A under an old scope can't keep silently suppressing its deduction.
    """
    applicable = conditional_na_applicable(scope, catalog)
    new = dict(assessment)
    reset_ids = []
    for cid, status in assessment.items():
        if status == NA_NOT_PERMITTED and cid not in applicable:
            new[cid] = NOT_IMPLEMENTED
            reset_ids.append(cid)
    reset_ids.sort(key=lambda c: tuple(int(p) for p in c.split(".")))
    return new, reset_ids
