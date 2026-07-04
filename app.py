"""CMMC Vault — NIST SP 800-171 self-assessment workspace (demo).

Session-only demo build: no accounts, nothing stored server-side. Every
visitor starts fresh; use the sidebar to load the sample company.
"""

import io
import json
from datetime import date, datetime

import pandas as pd
import streamlit as st

import disclosures
from export.binder import build_binder
from persistence import SCHEMA_VERSION, md_escape, sanitize_import
from logic.catalog import controls, load_sample, meta, poam_rules
from logic.scoring import (
    CONDITIONAL_THRESHOLD, IMPLEMENTED, NA_NOT_PERMITTED, NOT_IMPLEMENTED,
    PARTIAL_ALT, allowed_statuses, family_rollup, score_assessment,
)
from logic.readiness import (
    LBL_MANDATORY, blocker_first_path, conditional_eligibility,
    control_labels, dashboard_summary, evidence_index_from_register, poam_clock,
    poam_eligible,
)
from logic.scoping import (
    ASSET_CATEGORIES, conditional_na_applicable, reconcile_na_statuses,
)

st.set_page_config(
    page_title="CMMC Vault — 800-171 Self-Assessment",
    page_icon="🛡️",
    layout="wide",
)

CAT = controls()
BY_ID = {c["id"]: c for c in CAT}
META = meta()
RULES = poam_rules()

STATUS_LABELS_DEFAULT = {
    IMPLEMENTED: "✅ Implemented",
    NOT_IMPLEMENTED: "🔴 Not implemented",
}
STATUS_LABELS_MFA = {
    IMPLEMENTED: "✅ Fully implemented (all users)",
    PARTIAL_ALT: "🟠 Remote & privileged users only (−3)",
    NOT_IMPLEMENTED: "🔴 Not implemented (−5)",
}
STATUS_LABELS_FIPS = {
    IMPLEMENTED: "✅ FIPS-validated cryptography in use",
    PARTIAL_ALT: "🟠 Encryption in use, not FIPS-validated (−3)",
    NOT_IMPLEMENTED: "🔴 No encryption employed (−5)",
}
STATUS_LABELS_COND = {
    IMPLEMENTED: "✅ Implemented",
    NOT_IMPLEMENTED: "🔴 Not implemented",
    NA_NOT_PERMITTED: "➖ N/A — capability not permitted (document the policy)",
}


def labels_for(control):
    if control["special"] == "mfa":
        return STATUS_LABELS_MFA
    if control["special"] == "fips":
        return STATUS_LABELS_FIPS
    if control["conditional_na"]:
        return STATUS_LABELS_COND
    return STATUS_LABELS_DEFAULT


DEFAULT_SCOPE = {
    "handles_cui": True, "remote_access_permitted": True,
    "wireless_permitted": True, "mobile_permitted": True,
    "confirmed_at": None,
}


# ---------------------------------------------------------------- state ----
def init_state():
    ss = st.session_state
    ss.setdefault("assessment", {c["id"]: NOT_IMPLEMENTED for c in CAT})
    ss.setdefault("poam", {})       # id -> {"target_date": iso}
    ss.setdefault("evidence", {})   # id -> [register entries]
    ss.setdefault("scope", dict(DEFAULT_SCOPE))
    ss.setdefault("scope_assets", [])  # [{"name","category","description"}]
    ss.setdefault("company", "")


def load_sample_state():
    s = load_sample()
    st.session_state.assessment = dict(s["statuses"])
    st.session_state.poam = {k: dict(v) for k, v in s["poam"].items()}
    st.session_state.evidence = {k: [dict(e) for e in v] for k, v in s["evidence"].items()}
    st.session_state.company = s["company"]
    st.session_state.scope = dict(s.get("scope", DEFAULT_SCOPE))
    st.session_state.scope_assets = [dict(a) for a in s.get("scope_assets", [])]
    _clear_widget_keys()


def reset_state():
    st.session_state.assessment = {c["id"]: NOT_IMPLEMENTED for c in CAT}
    st.session_state.poam = {}
    st.session_state.evidence = {}
    st.session_state.scope = dict(DEFAULT_SCOPE)
    st.session_state.scope_assets = []
    st.session_state.company = ""
    _clear_widget_keys()


def _clear_widget_keys():
    # Per-control status/POA&M widget keys (prefixed), plus the data-editor and
    # transient keys that otherwise retain stale edits/messages across Reset/Load.
    # ('u_' is retired — the evidence file_uploader was replaced by the register.
    #  'import_json' can't be cleared programmatically in Streamlit; leave it.
    #  'fam_filter' is a view filter, intentionally preserved.)
    for k in list(st.session_state.keys()):
        if k.startswith(("w_", "p_", "d_")):
            del st.session_state[k]
    for k in ("ev_editor", "scope_assets_editor", "_import_warnings"):
        st.session_state.pop(k, None)


def _on_status_change(cid):
    st.session_state.assessment[cid] = st.session_state[f"w_{cid}"]
    if st.session_state.assessment[cid] == IMPLEMENTED:
        st.session_state.poam.pop(cid, None)


def _on_poam_toggle(cid):
    if st.session_state[f"p_{cid}"]:
        st.session_state.poam.setdefault(
            cid, {"target_date": date.today().isoformat()})
    else:
        st.session_state.poam.pop(cid, None)


def _on_poam_date(cid):
    st.session_state.poam[cid] = {
        "target_date": st.session_state[f"d_{cid}"].isoformat()}


def _evidence_index():
    return evidence_index_from_register(st.session_state.get("evidence", {}))


init_state()
NA_APPLICABLE = conditional_na_applicable(st.session_state.scope, CAT)
SCOPE_CONFIRMED = bool(st.session_state.scope.get("confirmed_at"))
RESULT = score_assessment(st.session_state.assessment, CAT)
EVIDENCE_INDEX = _evidence_index()
ELIG = conditional_eligibility(st.session_state.assessment, CAT, RULES)
SUMMARY = dashboard_summary(st.session_state.assessment, CAT, RULES, EVIDENCE_INDEX)
VERDICT = ("Projected: Final-ready" if SUMMARY.final_ready
           else "Projected: Conditional-eligible" if SUMMARY.conditional_eligible
           else "Not conditionally ready")


# -------------------------------------------------------------- sidebar ----
with st.sidebar:
    st.markdown("### 🛡️ CMMC Vault")
    st.caption("NIST SP 800-171 Rev 2 self-assessment workspace · **demo build**")
    st.text_input("Organization", key="company", placeholder="Your company name")
    c1, c2 = st.columns(2)
    c1.button("Load sample", on_click=load_sample_state, use_container_width=True)
    c2.button("Reset", on_click=reset_state, use_container_width=True)
    st.divider()

    up = st.file_uploader("Resume: import a saved assessment (.json)", type="json",
                          key="import_json")
    if up is not None and not st.session_state.get("_imported_" + str(up.file_id), False):
        try:
            payload = json.loads(up.getvalue().decode("utf-8"))
            state, warns = sanitize_import(payload, CAT)
            for k, v in state.items():
                st.session_state[k] = v
            _clear_widget_keys()
            st.session_state["_imported_" + str(up.file_id)] = True
            st.session_state["_import_warnings"] = warns
            st.rerun()
        except (ValueError, UnicodeDecodeError):
            st.error("That file isn't valid JSON — nothing was imported.")
    for w in st.session_state.get("_import_warnings", [])[:8]:
        st.caption("⚠️ " + md_escape(w))

    export = {
        "schema_version": SCHEMA_VERSION,
        "company": st.session_state.company,
        "exported": datetime.now().isoformat(timespec="seconds"),
        "score": RESULT.score,   # informational only; import recomputes and ignores this
        "statuses": st.session_state.assessment,
        "poam": st.session_state.poam,
        "evidence": st.session_state.evidence,
        "scope": st.session_state.scope,
        "scope_assets": st.session_state.scope_assets,
    }
    st.download_button(
        "⬇️ Export assessment (JSON)",
        data=json.dumps(export, indent=2),
        file_name="800-171-self-assessment.json",
        mime="application/json",
        use_container_width=True,
    )
    st.download_button(
        "📄 Assessment Prep Binder (.docx)",
        data=build_binder(
            org_name=st.session_state.company, catalog=CAT,
            assessment=st.session_state.assessment, rules=RULES,
            evidence=st.session_state.evidence, poam=st.session_state.poam,
            today=date.today(),
        ),
        file_name="CMMC-Assessment-Prep-Binder.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        use_container_width=True,
    )
    st.caption(
        "Session-only: nothing is intentionally persisted — your work is held in "
        "temporary Streamlit server memory only for this session. **Export before "
        "closing the tab**, and re-import to resume."
    )

# --------------------------------------------------------------- header ----
# Persistent demo-safety banner (always visible, above every tab).
st.warning(disclosures.DEMO_BANNER, icon="⚠️")

title = st.session_state.company.strip() or "Untitled assessment"
st.markdown(f"## {md_escape(title)}")

if RESULT.ssp_missing:
    st.error(
        "**No System Security Plan (3.12.4).** Under the DoD methodology, "
        "without an SSP the assessment *cannot be completed* — there is no "
        "valid score to post to SPRS. The number below is for planning only. "
        "Mark 3.12.4 implemented once your SSP exists.",
        icon="🚫",
    )

# Readiness verdict — the compound gate, NOT the raw score. This is the whole point:
# a score at or above 88 is necessary but not sufficient for Conditional status.
if SUMMARY.conditional_eligible:
    st.success(f"**Score {RESULT.score} — {VERDICT}**", icon="✅")
else:
    st.error(f"**Score {RESULT.score} — Not conditionally ready**", icon="🛑")
    if SUMMARY.score >= CONDITIONAL_THRESHOLD:
        st.markdown(
            f"You're **at or above 88**, but **{len(ELIG.blocking_ids)} open "
            "requirement(s) cannot be deferred to a POA&M** — so you are not yet "
            "eligible for Conditional status. Reaching 88 is necessary, not sufficient."
        )
st.caption(disclosures.READINESS_QUALIFIER)

m1, m2, m3, m4 = st.columns(4)
m1.metric("SPRS score", RESULT.score, help="DoD Assessment Methodology range: −203 to 110")
m2.metric("Implemented", f"{RESULT.implemented_count}/110")
m3.metric("Blockers (can't POA&M)", len(ELIG.blocking_ids),
          help="Open requirements that are NOT POA&M-eligible under 32 CFR 170.21 — "
               "they must be MET at assessment and block Conditional status regardless of score.")
m4.metric("Projected readiness", VERDICT.replace("Projected: ", ""))

st.progress(
    min(max((RESULT.score + 203) / 313, 0.0), 1.0),
    text="Score on the −203 … 110 scale · **88 is the point *floor* for Conditional — "
         "necessary, not sufficient**",
)

tab_dash, tab_scope, tab_assess, tab_ev, tab_path, tab_poam, tab_about = st.tabs(
    ["📊 Dashboard", "🧭 Scope", "📋 Assessment", "📎 Evidence",
     "🎯 Blocker-First Readiness Path", "🗂️ POA&M", "ℹ️ Method & sources"]
)

# ----------------------------------------------------------------- scope ----
with tab_scope:
    st.markdown("#### Define your assessment scope first")
    st.caption(
        "Scope decides which requirements even apply. You must confirm scope before "
        "marking any control 'N/A — capability not permitted' — otherwise it's too "
        "easy to zero out a requirement for a capability you actually use."
    )
    if not SCOPE_CONFIRMED:
        st.warning("Scope not confirmed yet — 'N/A' options are disabled in the "
                   "Assessment tab until you confirm below.", icon="🧭")
    else:
        st.success(f"Scope confirmed {st.session_state.scope['confirmed_at']}. "
                   f"N/A is available for: {', '.join(sorted(NA_APPLICABLE)) or '(none)'}.")

    sc = st.session_state.scope
    with st.form("scope_form"):
        st.markdown("**Capabilities in your environment** "
                    "(unchecking a box lets its controls be marked N/A):")
        f_cui = st.checkbox("We process, store, or transmit CUI", value=sc["handles_cui"])
        f_remote = st.checkbox("Remote access is permitted", value=sc["remote_access_permitted"])
        f_wifi = st.checkbox("Wireless access is permitted", value=sc["wireless_permitted"])
        f_mobile = st.checkbox("Mobile devices are permitted", value=sc["mobile_permitted"])
        submitted = st.form_submit_button("✅ Confirm scope", use_container_width=True)
    if submitted:
        st.session_state.scope = {
            "handles_cui": f_cui, "remote_access_permitted": f_remote,
            "wireless_permitted": f_wifi, "mobile_permitted": f_mobile,
            "confirmed_at": date.today().isoformat(),
        }
        new_assessment, reset_ids = reconcile_na_statuses(
            st.session_state.assessment, st.session_state.scope, CAT)
        st.session_state.assessment = new_assessment
        _clear_widget_keys()
        if reset_ids:
            st.warning("Scope change reset these controls from N/A back to "
                       "'Not implemented' (the capability is now in scope): "
                       + ", ".join(reset_ids), icon="♻️")
        st.rerun()

    st.divider()
    st.markdown("#### Asset inventory (minimal)")
    st.caption("Tag each asset with its CMMC Level 2 scoping category. Do not enter "
               "hostnames, IPs, or system identifiers — use generic names.")
    edited = st.data_editor(
        st.session_state.scope_assets or [{"name": "", "category": ASSET_CATEGORIES[0], "description": ""}],
        num_rows="dynamic", use_container_width=True, key="scope_assets_editor",
        column_config={
            "category": st.column_config.SelectboxColumn("category", options=ASSET_CATEGORIES),
        },
    )
    st.session_state.scope_assets = [r for r in edited if r.get("name")]
    st.caption("Scope defines the boundary; an asset inventory, SSP, and network "
               "diagram are the three artifacts assessors expect. (This tool does not "
               "generate a network diagram — that's on your checklist.)")

# ------------------------------------------------------------- dashboard ----
with tab_dash:
    st.markdown("#### Projected readiness (self-estimate)")
    rc1, rc2, rc3 = st.columns(3)
    rc1.metric("Score", SUMMARY.score)
    rc2.metric("Conditional-eligible?", "Yes" if SUMMARY.conditional_eligible else "No")
    cov = f"{SUMMARY.evidence_covered}/{SUMMARY.evidence_applicable}"
    rc3.metric("Evidence register coverage", cov,
               help="In-scope controls with a register entry that is document-final, "
                    "demonstrably operational, AND reviewed.")

    if ELIG.blocking_ids:
        st.markdown("**🛑 Blockers — cannot be deferred to a POA&M (must be MET):**")
        for cid in ELIG.blocking_ids:
            c = BY_ID[cid]
            w = "SSP" if c["weight"] == "NA" else f'{c["max_deduction"]} pt'
            st.markdown(f"- **{cid}** · {w} — {c['short_title']}")
    if SUMMARY.prime_risks:
        with st.expander("Risks that undercut prime/customer confidence", expanded=False):
            for r in SUMMARY.prime_risks:
                st.markdown(f"- {r}")
    oc1, oc2, oc3 = st.columns(3)
    oc1.metric("Open 5-pt", SUMMARY.open_5pt)
    oc2.metric("Open 3-pt", SUMMARY.open_3pt)
    oc3.metric("Open 1-pt", SUMMARY.open_1pt)
    st.divider()

    left, right = st.columns([3, 2], gap="large")
    with left:
        st.markdown("#### Points by control family")
        rows = family_rollup(st.session_state.assessment, CAT)
        df = pd.DataFrame([{
            "Family": f'{r["family"]} {r["family_name"]}',
            "Implemented": f'{r["implemented"]}/{r["controls"]}',
            "Points kept": r["points_kept"],
            "Possible": r["points_possible"],
            "Share": r["pct_kept"],
        } for r in rows])
        st.dataframe(
            df,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Share": st.column_config.ProgressColumn(
                    "Points kept", min_value=0, max_value=1, format="%.0f%%"),
                "Points kept": None,
            },
        )
    with right:
        st.markdown("#### Biggest open gaps")
        gaps = sorted(
            ((cid, d) for cid, d in RESULT.per_control.items() if d > 0),
            key=lambda x: -x[1])[:6]
        if not gaps:
            st.success("No open gaps — perfect score. Time to document it.")
        for cid, d in gaps:
            c = BY_ID[cid]
            st.markdown(
                f"**−{d} · {cid} — {c['short_title']}**  \n"
                f"<span style='color:#5b6b7a;font-size:0.85em'>{c['requirement'][:110]}…</span>",
                unsafe_allow_html=True,
            )
        if not SUMMARY.conditional_eligible:
            st.info(
                "The **Blocker-First Readiness Path** tab turns this into an ordered "
                "work plan — mandatory (non-deferrable) items first."
            )

# ------------------------------------------------------------ assessment ----
with tab_assess:
    fam_options = ["All families"] + [
        f'{code} — {name}' for code, name in sorted(
            {(c["family"], c["family_name"]) for c in CAT},
            key=lambda t: tuple(int(x) for x in t[0].split(".")))
    ]
    pick = st.selectbox("Filter by family", fam_options, key="fam_filter")
    show = CAT if pick == "All families" else [
        c for c in CAT if c["family"] == pick.split(" — ")[0]]

    hide_done = st.toggle("Show only open items", value=False)
    labels = control_labels(st.session_state.assessment, CAT, RULES, EVIDENCE_INDEX)
    for c in show:
        cid = c["id"]
        status = st.session_state.assessment.get(cid, NOT_IMPLEMENTED)
        if hide_done and status in (IMPLEMENTED, NA_NOT_PERMITTED):
            continue
        d = RESULT.per_control.get(cid, 0)
        icon = "✅" if d == 0 and status in (IMPLEMENTED, NA_NOT_PERMITTED) else ("🟠" if status == PARTIAL_ALT else "🔴")
        weight_txt = "SSP — required" if c["weight"] == "NA" else f'{c["weight"]} pt'
        ev_n = len(st.session_state.evidence.get(cid, []))
        badge = f" · 📎{ev_n}" if ev_n else ""
        lbl = labels.get(cid, {})
        blocker_badge = "  🛑" if lbl.get("primary") == LBL_MANDATORY else ""
        with st.expander(f"{icon} **{cid}** — {c['short_title']} · {weight_txt}{badge}{blocker_badge}"):
            if lbl.get("tags"):
                st.caption("Readiness: " + " · ".join(lbl["tags"]))
            st.caption(c["requirement"])
            opts = allowed_statuses(c)
            # Gate the "N/A — not permitted" option: only when scope earns it.
            if NA_NOT_PERMITTED in opts and cid not in NA_APPLICABLE:
                opts = [o for o in opts if o != NA_NOT_PERMITTED]
                if c.get("conditional_na") and not SCOPE_CONFIRMED:
                    st.caption("➖ Confirm scope (Scope tab) to enable 'N/A — capability "
                               "not permitted' for this control.")
            status_lbls = labels_for(c)
            st.radio(
                "Status", opts,
                index=opts.index(status) if status in opts else opts.index(NOT_IMPLEMENTED),
                format_func=lambda s, _l=status_lbls: _l[s],
                key=f"w_{cid}", on_change=_on_status_change, args=(cid,),
                horizontal=False, label_visibility="collapsed",
            )
            if c["guidance"]:
                g = c["guidance"]
                if not g.get("reviewed", False):
                    st.caption("📝 *Draft guidance — pending expert review.*")
                st.info(
                    f"**In plain English:** {g['plain']}\n\n"
                    f"**Evidence that satisfies an assessor:** {g['evidence']}\n\n"
                    f"**Quick win:** {g['quick_win']}"
                )
            if status not in (IMPLEMENTED, NA_NOT_PERMITTED):
                pc1, pc2 = st.columns([1, 2])
                pc1.checkbox("Track on POA&M", value=cid in st.session_state.poam,
                             key=f"p_{cid}", on_change=_on_poam_toggle, args=(cid,))
                if cid in st.session_state.poam:
                    pc2.date_input(
                        "Target completion",
                        value=date.fromisoformat(
                            st.session_state.poam[cid]["target_date"]),
                        key=f"d_{cid}", on_change=_on_poam_date, args=(cid,),
                    )
            # Evidence is a metadata REGISTER (no files stored). Read-only summary
            # here; the editable register lives in its own step (P1.3).
            for e in st.session_state.evidence.get(cid, []):
                st.caption(
                    f"📋 **{md_escape(e.get('title', 'evidence'))}** — owner: "
                    f"{md_escape(e.get('owner', '—'))} · "
                    f"{e.get('doc_status', '?')}/{e.get('impl_status', '?')}/"
                    f"{e.get('review_status', '?')} · {md_escape(e.get('location_uri', ''))}"
                )

DOC_STATUSES = ["missing", "draft", "final"]
IMPL_STATUSES = ["documented_only", "partially_operational", "demonstrates_operation"]
REVIEW_STATUSES = ["unreviewed", "reviewed"]
_EV_FIELDS = ("title", "owner", "location_uri", "doc_status", "impl_status", "review_status")

# -------------------------------------------------------------- evidence ----
with tab_ev:
    st.markdown("#### Evidence register")
    st.info(disclosures.DATA_BOUNDARY, icon="🔒")
    if not SCOPE_CONFIRMED:
        st.warning("Confirm your assessment scope first (🧭 Scope tab) — evidence "
                   "planning comes after you've defined the boundary.", icon="🧭")
    else:
        st.caption(
            "Track WHAT evidence each control needs, WHERE it lives, WHO owns it, and "
            "three separate things: is the **document** final, does it **demonstrate "
            "operation** (a signed-but-unimplemented policy is NOT operational), and "
            "has it been **reviewed**. No files are stored — this is a register of pointers."
        )
        rows = []
        for cid, entries in st.session_state.evidence.items():
            for e in entries:
                rows.append({"control": cid, **{k: e.get(k) for k in _EV_FIELDS}})
        if not rows:
            rows = [{"control": "3.1.1", "title": "", "owner": "", "location_uri": "",
                     "doc_status": "missing", "impl_status": "documented_only",
                     "review_status": "unreviewed"}]
        edited = st.data_editor(
            rows, num_rows="dynamic", use_container_width=True, key="ev_editor",
            column_config={
                "control": st.column_config.SelectboxColumn(
                    "control", options=[c["id"] for c in CAT], required=True),
                "location_uri": st.column_config.TextColumn(
                    "location (pointer, not the file)"),
                "doc_status": st.column_config.SelectboxColumn("document", options=DOC_STATUSES),
                "impl_status": st.column_config.SelectboxColumn("implementation", options=IMPL_STATUSES),
                "review_status": st.column_config.SelectboxColumn("review", options=REVIEW_STATUSES),
            },
        )
        newev = {}
        for r in edited:
            if r.get("title") and r.get("control"):
                newev.setdefault(r["control"], []).append(
                    {k: r.get(k) for k in _EV_FIELDS})
        # If the register actually changed, persist and rerun so the top-of-page
        # SUMMARY (and the Dashboard coverage metric) reflect it immediately rather
        # than lagging one interaction. One extra rerun only on real change; no loop.
        if newev != st.session_state.evidence:
            st.session_state.evidence = newev
            st.rerun()
        st.success(
            f"**Evidence register coverage: {SUMMARY.evidence_covered}/"
            f"{SUMMARY.evidence_applicable}** in-scope controls have an entry that is "
            "document-final, demonstrably operational, AND reviewed.")
        if SUMMARY.controls_without_operational_evidence:
            st.caption("First controls still lacking operational, reviewed evidence: "
                       + ", ".join(SUMMARY.controls_without_operational_evidence[:12]))

# ------------------------------------------------ blocker-first readiness path ----
with tab_path:
    st.markdown("#### Blocker-First Readiness Path")
    st.caption(
        "Not merely 'fastest to 88.' Under 32 CFR 170.21, some open requirements "
        "**cannot be deferred to a POA&M** — they must be MET. This plan fixes the "
        "SSP (if missing) first, then every non-deferrable blocker, then the highest-"
        "value POA&M-eligible items until the 88-point floor is cleared. It often "
        "**overshoots 88 — that is the honest answer.**"
    )
    steps = blocker_first_path(st.session_state.assessment, CAT, RULES)
    if not steps:
        st.success("No open requirements — every measure is met. Time to document it.")
    else:
        pdf_rows = []
        for i, s in enumerate(steps, 1):
            c = BY_ID[s["id"]]
            if s["required_first"]:
                kind = "SSP — required first"
            elif s["mandatory"]:
                kind = "🛑 Mandatory (can't POA&M)"
            else:
                kind = "POA&M-eligible"
            pdf_rows.append({
                "Step": i,
                "Control": s["id"],
                "What": c["short_title"],
                "Type": kind,
                "Points": ("required" if s["required_first"] else f'+{s["gain"]}'),
                "Score after": s["score_after"],
                "Eligible after?": "✅" if s["eligible_after"] else "—",
            })
        st.dataframe(pd.DataFrame(pdf_rows), hide_index=True, use_container_width=True)
        last = steps[-1]
        n_mand = len([s for s in steps if s["mandatory"] and not s["required_first"]])
        if last["eligible_after"]:
            st.success(
                f"Projected **Conditional-eligible** once these are complete "
                f"(score **{last['score_after']}**) — including **{n_mand} non-deferrable "
                "blocker(s)** that must be met no matter the point math."
            )
        else:
            st.warning(
                "This plan lists the mandatory blockers; more POA&M-eligible work may "
                "remain to clear the 88-point floor. " + disclosures.READINESS_QUALIFIER
            )

# ------------------------------------------------------------------ poam ----
with tab_poam:
    st.markdown("#### Plan of Action & Milestones")
    st.caption(
        "Per the DoD methodology: an item on a POA&M still scores as *not "
        "implemented* until finished — and open items **without** a plan of "
        "action cause 3.12.2 itself to be scored not implemented."
    )
    if not st.session_state.poam:
        st.info("No POA&M items yet. Flag any open control from the Assessment tab.")
    else:
        rows, ineligible = [], []
        for cid, p in sorted(st.session_state.poam.items()):
            c = BY_ID[cid]
            tgt = date.fromisoformat(p["target_date"])
            status = st.session_state.assessment.get(cid, NOT_IMPLEMENTED)
            elig = poam_eligible(c, status, RULES)
            if not elig:
                ineligible.append(cid)
            rows.append({
                "Control": cid,
                "Requirement (short)": c["short_title"],
                "Points at stake": RESULT.per_control.get(cid, 0),
                "POA&M-eligible?": "Yes" if elig else "NO — must be MET",
                "Target date": tgt.isoformat(),
                "Days remaining": (tgt - date.today()).days,
            })
        if ineligible:
            st.error(
                "**These POA&M items are NOT eligible for a POA&M under 32 CFR 170.21 "
                "and must be MET at assessment:** " + ", ".join(ineligible) +
                ". Listing them on a POA&M will not make you Conditional-eligible.",
                icon="🛑",
            )
        pdf = pd.DataFrame(rows)
        st.dataframe(pdf, hide_index=True, use_container_width=True)
        buf = io.StringIO()
        pdf.to_csv(buf, index=False)
        st.download_button("⬇️ Download POA&M (CSV)", buf.getvalue(),
                           file_name="poam.csv", mime="text/csv")

    st.divider()
    st.markdown("##### 180-day Conditional → Final countdown")
    st.caption("If you have been granted Conditional CMMC status, enter its **actual** "
               "date (from your assessment) — the 180-day POA&M closeout clock is "
               "anchored only to that real date, never projected from this tool.")
    use_clock = st.checkbox("I have an actual Conditional status date")
    if use_clock:
        cdate = st.date_input("Conditional status date", value=date.today())
        clock = poam_clock(cdate, date.today())
        if clock["expired"]:
            st.error(f"POA&M closeout deadline {clock['deadline']} has **passed** "
                     f"({-clock['days_remaining']} days ago) — Conditional status expires "
                     "if not closed out.")
        else:
            st.info(f"POA&M closeout deadline: **{clock['deadline']}** "
                    f"({clock['days_remaining']} days remaining).")

# ----------------------------------------------------------------- about ----
with tab_about:
    st.markdown("#### Scoring method")
    st.markdown(
        "- Start at **110**. Each requirement not implemented subtracts its "
        "weighted value (**5 / 3 / 1**). Floor: **−203**.\n"
        "- **3.5.3 MFA** and **3.13.11 FIPS cryptography** carry built-in partial "
        "credit: −3 instead of −5 for the partial condition.\n"
        "- **3.1.12/13 (remote access), 3.1.16/17 (wireless), 3.1.18 (mobile):** "
        "no deduction if the capability is not permitted at all — but have the "
        "policy in writing.\n"
        "- **3.12.4 System Security Plan:** carries no point value; without an "
        "SSP the assessment cannot be completed and no score exists.\n"
        f"- **{CONDITIONAL_THRESHOLD}** = 80% of 110 is the point **floor** for "
        "Conditional status — **necessary but not sufficient** (see below)."
    )
    st.markdown("#### Why 88 is not enough — the compound gate (32 CFR 170.21)")
    st.markdown(
        "Reaching 88 lets you *seek* Conditional status, but a POA&M is permitted "
        "only if **every** open requirement on it is POA&M-eligible:\n"
        "- Items worth **more than 1 point are not POA&M-eligible** — except "
        "**3.13.11** (CUI encryption) at the −3 partial (encryption in use, not "
        "FIPS-validated).\n"
        "- Six 1-point requirements are **never** POA&M-eligible: "
        "**3.1.20, 3.1.22, 3.12.4 (SSP), 3.10.3, 3.10.4, 3.10.5**.\n"
        "- POA&M items must be closed out within **180 days** of the Conditional "
        "status date, or it expires."
    )
    st.markdown("#### What this tool's readiness means vs. official CMMC status")
    st.table({
        "This tool shows (self-estimate)": [r[0] for r in disclosures.APP_TO_CMMC_STATUS],
        "Official CMMC meaning": [r[1] for r in disclosures.APP_TO_CMMC_STATUS],
        "How it is actually earned": [r[2] for r in disclosures.APP_TO_CMMC_STATUS],
    })
    st.caption("This tool confers **none** of these statuses.")
    st.markdown("#### Data provenance")
    st.markdown(
        f"Control weights transcribed **{META['transcribed']}** from *{META['source']}*. "
        "Build-time validation asserts the exact published distribution "
        "(44 × 5-pt incl. two 5/3 specials, 14 × 3-pt, 51 × 1-pt, 1 × NA) and the "
        "−203 floor, so the data cannot silently drift from the methodology."
    )
    st.warning(disclosures.DISCLAIMER, icon="⚖️")

    st.divider()
    st.markdown("#### About this tool & its limitations")
    st.markdown(
        "**What it is:** a self-assessment aid and a guided readiness conversation "
        "tool — a self-estimate.\n\n"
        "**What it does:** computes the SPRS score and the *compound* Conditional-"
        "eligibility verdict (32 CFR 170.21), surfaces blockers, organizes evidence "
        "*planning* metadata, and exports an Assessment Prep Binder.\n\n"
        "**What it cannot do / is not:** it is not a certification, not legal advice, "
        "not a C3PAO assessment, and confers no CMMC status. It stores nothing "
        "(session-only). \n\n"
        "**Current-state limits:** guidance marked *draft* is not yet expert-reviewed; "
        "control weights are transcribed and should be spot-checked against the "
        "official DoD methodology; self-reported fields are your claims, not verified."
    )
    st.info(disclosures.DATA_BOUNDARY, icon="🔒")
    st.caption("Operating posture: " + disclosures.OPERATING_POSTURE)
