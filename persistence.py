"""Validated import of a previously-exported session JSON.

The demo would otherwise crash on a hand-edited or stale file: the frozen
`deduction_for` raises on an out-of-range status, and a bad date crashes the POA&M
tab. This module coerces untrusted input into a safe state and NEVER trusts the
embedded score (it is recomputed downstream). Pure: no Streamlit, no I/O.
"""

import re
from datetime import date

from logic.scoring import (
    NOT_IMPLEMENTED, allowed_statuses,
)
from logic.scoping import ASSET_CATEGORIES, reconcile_na_statuses

SCHEMA_VERSION = 1

# Markdown metacharacters that could turn an imported free-text field into a link,
# image (remote beacon), heading, or code when rendered by st.markdown/st.caption.
# Streamlit already blocks script/HTML; this stops Markdown-syntax phishing/beacons.
_MD_META = re.compile(r"([`*_\[\]()#!<>|~])")


def md_escape(value) -> str:
    return _MD_META.sub(r"\\\1", str(value or ""))


def _valid_date(value) -> bool:
    """A calendar-valid ISO date. A bare regex would accept '2026-99-99', which then
    crashes date.fromisoformat downstream and takes the whole app down."""
    try:
        date.fromisoformat(str(value))
        return True
    except (ValueError, TypeError):
        return False
_UNSAFE_SCHEME = re.compile(r"^\s*(javascript|data|vbscript|file):", re.IGNORECASE)
_EV_FIELDS = ("title", "owner", "location_uri", "doc_status", "impl_status", "review_status")
_DOC = {"missing", "draft", "final"}
_IMPL = {"documented_only", "partially_operational", "demonstrates_operation"}
_REVIEW = {"unreviewed", "reviewed"}


def sanitize_uri(value) -> str:
    s = str(value or "")
    if _UNSAFE_SCHEME.match(s):
        return "(unsafe link removed)"
    return s


def sanitize_import(payload: dict, catalog: list) -> tuple:
    """Return (state, warnings). `state` has company/assessment/poam/evidence/scope/
    scope_assets ready to drop into session. `warnings` explains every coercion."""
    warnings = []
    if not isinstance(payload, dict):
        return _empty_state(catalog), ["File was not a valid assessment object; nothing imported."]

    by_id = {c["id"]: c for c in catalog}

    # ---- statuses ----
    assessment = {c["id"]: NOT_IMPLEMENTED for c in catalog}
    raw_status = payload.get("statuses", {})
    if isinstance(raw_status, dict):
        for cid, status in raw_status.items():
            c = by_id.get(cid)
            if c is None:
                warnings.append(f"Dropped unknown control id '{cid}'.")
                continue
            if status in allowed_statuses(c):
                assessment[cid] = status
            else:
                assessment[cid] = NOT_IMPLEMENTED
                warnings.append(f"{cid}: status '{status}' not valid here — set to 'not implemented'.")

    # ---- poam ----
    poam = {}
    raw_poam = payload.get("poam", {})
    if isinstance(raw_poam, dict):
        for cid, p in raw_poam.items():
            if cid not in by_id:
                warnings.append(f"Dropped POA&M for unknown control '{cid}'.")
                continue
            tgt = (p or {}).get("target_date", "") if isinstance(p, dict) else ""
            if not _valid_date(tgt):
                warnings.append(f"{cid}: invalid POA&M date '{tgt}' — dropped.")
                continue
            poam[cid] = {"target_date": tgt}

    # ---- evidence (new register shape, or legacy id->[filenames]) ----
    evidence, ev_warn = _import_evidence(payload.get("evidence", {}), by_id)
    warnings.extend(ev_warn)

    # ---- scope ----
    scope = _import_scope(payload.get("scope"))
    scope_assets = _import_scope_assets(payload.get("scope_assets"))

    # Enforce the scope-earned-N/A invariant on import: an imported file could carry
    # an N/A status the imported scope no longer earns (silent score inflation, and
    # screen/score disagreement). Reconcile and report.
    assessment, reset_ids = reconcile_na_statuses(assessment, scope, catalog)
    if reset_ids:
        warnings.append("Reset N/A -> 'not implemented' (scope does not permit N/A "
                        "for these): " + ", ".join(reset_ids) + ".")

    company = str(payload.get("company", "") or "")
    state = {
        "company": company, "assessment": assessment, "poam": poam,
        "evidence": evidence, "scope": scope, "scope_assets": scope_assets,
    }
    return state, warnings


def _import_evidence(raw, by_id):
    warnings = []
    out = {}
    if not isinstance(raw, dict):
        return out, warnings
    for cid, entries in raw.items():
        if cid not in by_id:
            warnings.append(f"Dropped evidence for unknown control '{cid}'.")
            continue
        if not isinstance(entries, list):
            continue
        migrated = []
        for e in entries:
            if isinstance(e, str):
                # legacy shape: a filename string -> a draft register pointer
                migrated.append({
                    "title": e, "owner": "", "location_uri": "",
                    "doc_status": "draft", "impl_status": "documented_only",
                    "review_status": "unreviewed",
                })
                warnings.append(f"{cid}: migrated legacy evidence filename '{e}' to a draft register entry.")
            elif isinstance(e, dict):
                migrated.append({
                    "title": str(e.get("title", "") or ""),
                    "owner": str(e.get("owner", "") or ""),
                    "location_uri": sanitize_uri(e.get("location_uri", "")),
                    "doc_status": e.get("doc_status") if e.get("doc_status") in _DOC else "missing",
                    "impl_status": e.get("impl_status") if e.get("impl_status") in _IMPL else "documented_only",
                    "review_status": e.get("review_status") if e.get("review_status") in _REVIEW else "unreviewed",
                })
        if migrated:
            out[cid] = migrated
    return out, warnings


def _import_scope_assets(raw):
    """Keep only well-formed asset rows; coerce fields to strings and whitelist the
    category. Prevents a crafted file from crashing the Scope tab or bloating session."""
    if not isinstance(raw, list):
        return []
    out = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        cat = item.get("category")
        out.append({
            "name": str(item.get("name", "") or "")[:200],
            "category": cat if cat in ASSET_CATEGORIES else ASSET_CATEGORIES[0],
            "description": str(item.get("description", "") or "")[:1000],
        })
    return out


def _import_scope(raw):
    default = {
        "handles_cui": True, "remote_access_permitted": True,
        "wireless_permitted": True, "mobile_permitted": True, "confirmed_at": None,
    }
    if not isinstance(raw, dict):
        return default
    out = dict(default)
    for k in ("handles_cui", "remote_access_permitted", "wireless_permitted", "mobile_permitted"):
        if isinstance(raw.get(k), bool):
            out[k] = raw[k]
    ca = raw.get("confirmed_at")
    out["confirmed_at"] = ca if (ca is None or _valid_date(ca)) else None
    return out


def _empty_state(catalog):
    return {
        "company": "", "assessment": {c["id"]: NOT_IMPLEMENTED for c in catalog},
        "poam": {}, "evidence": {},
        "scope": _import_scope(None), "scope_assets": [],
    }
