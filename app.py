"""CMMC Vault — NIST SP 800-171 self-assessment workspace (demo).

Session-only demo build: no accounts, nothing stored server-side. Every
visitor starts fresh; use the sidebar to load the sample company.
"""

import io
import json
from datetime import date, datetime

import pandas as pd
import streamlit as st

from logic.catalog import controls, load_sample, meta
from logic.scoring import (
    CONDITIONAL_THRESHOLD, IMPLEMENTED, NA_NOT_PERMITTED, NOT_IMPLEMENTED,
    PARTIAL_ALT, allowed_statuses, family_rollup, fastest_path,
    score_assessment,
)

st.set_page_config(
    page_title="CMMC Vault — 800-171 Self-Assessment",
    page_icon="🛡️",
    layout="wide",
)

CAT = controls()
BY_ID = {c["id"]: c for c in CAT}
META = meta()

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


# ---------------------------------------------------------------- state ----
def init_state():
    ss = st.session_state
    ss.setdefault("assessment", {c["id"]: NOT_IMPLEMENTED for c in CAT})
    ss.setdefault("poam", {})       # id -> {"target_date": iso}
    ss.setdefault("evidence", {})   # id -> [filenames]
    ss.setdefault("company", "")


def load_sample_state():
    s = load_sample()
    st.session_state.assessment = dict(s["statuses"])
    st.session_state.poam = {k: dict(v) for k, v in s["poam"].items()}
    st.session_state.evidence = {k: list(v) for k, v in s["evidence"].items()}
    st.session_state.company = s["company"]
    _clear_widget_keys()


def reset_state():
    st.session_state.assessment = {c["id"]: NOT_IMPLEMENTED for c in CAT}
    st.session_state.poam = {}
    st.session_state.evidence = {}
    st.session_state.company = ""
    _clear_widget_keys()


def _clear_widget_keys():
    for k in list(st.session_state.keys()):
        if k.startswith(("w_", "p_", "d_", "u_")):
            del st.session_state[k]


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


init_state()
RESULT = score_assessment(st.session_state.assessment, CAT)


# -------------------------------------------------------------- sidebar ----
with st.sidebar:
    st.markdown("### 🛡️ CMMC Vault")
    st.caption("NIST SP 800-171 Rev 2 self-assessment workspace · **demo build**")
    st.text_input("Organization", key="company", placeholder="Your company name")
    c1, c2 = st.columns(2)
    c1.button("Load sample", on_click=load_sample_state, use_container_width=True)
    c2.button("Reset", on_click=reset_state, use_container_width=True)
    st.divider()
    export = {
        "company": st.session_state.company,
        "exported": datetime.now().isoformat(timespec="seconds"),
        "score": RESULT.score,
        "statuses": st.session_state.assessment,
        "poam": st.session_state.poam,
        "evidence": st.session_state.evidence,
    }
    st.download_button(
        "⬇️ Export assessment (JSON)",
        data=json.dumps(export, indent=2),
        file_name="800-171-self-assessment.json",
        mime="application/json",
        use_container_width=True,
    )
    st.caption(
        "Demo stores nothing server-side — data lives in this browser session "
        "only. Export before you close the tab."
    )

# --------------------------------------------------------------- header ----
title = st.session_state.company.strip() or "Untitled assessment"
st.markdown(f"## {title}")

if RESULT.ssp_missing:
    st.error(
        "**No System Security Plan (3.12.4).** Under the DoD methodology, "
        "without an SSP the assessment *cannot be completed* — there is no "
        "valid score to post to SPRS. The number below is for planning only. "
        "Mark 3.12.4 implemented once your SSP exists.",
        icon="🚫",
    )

m1, m2, m3, m4 = st.columns(4)
m1.metric("SPRS score", RESULT.score, help="DoD Assessment Methodology range: −203 to 110")
m2.metric("Implemented", f"{RESULT.implemented_count}/110")
m3.metric(f"Points to {CONDITIONAL_THRESHOLD}", RESULT.points_to_threshold,
          help="88 (80% of 110) is the CMMC Level 2 conditional-status minimum")
m4.metric("POA&M items", len(st.session_state.poam))

st.progress(
    min(max((RESULT.score + 203) / 313, 0.0), 1.0),
    text=f"−203 ─── 0 ─── **{CONDITIONAL_THRESHOLD} conditional threshold** ─── 110",
)

tab_dash, tab_assess, tab_path, tab_poam, tab_about = st.tabs(
    ["📊 Dashboard", "📋 Assessment", "🎯 Fastest path to 88", "🗂️ POA&M", "ℹ️ Method & sources"]
)

# ------------------------------------------------------------- dashboard ----
with tab_dash:
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
        if RESULT.points_to_threshold > 0:
            st.info(
                f"**{RESULT.points_to_threshold} points** separate you from the "
                f"{CONDITIONAL_THRESHOLD} threshold. The *Fastest path* tab turns "
                "that into an ordered work plan."
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
        with st.expander(f"{icon} **{cid}** — {c['short_title']} · {weight_txt}{badge}"):
            st.caption(c["requirement"])
            opts = allowed_statuses(c)
            lbl = labels_for(c)
            st.radio(
                "Status", opts,
                index=opts.index(status) if status in opts else opts.index(NOT_IMPLEMENTED),
                format_func=lambda s, _l=lbl: _l[s],
                key=f"w_{cid}", on_change=_on_status_change, args=(cid,),
                horizontal=False, label_visibility="collapsed",
            )
            if c["guidance"]:
                g = c["guidance"]
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
            up = st.file_uploader(
                "Attach evidence (demo: filenames only, files are not stored)",
                accept_multiple_files=True, key=f"u_{cid}")
            if up:
                names = st.session_state.evidence.setdefault(cid, [])
                for f in up:
                    if f.name not in names:
                        names.append(f.name)
            if ev_n or st.session_state.evidence.get(cid):
                st.caption("Evidence on file: " + ", ".join(
                    st.session_state.evidence.get(cid, [])))

# ----------------------------------------------------------- fastest path ----
with tab_path:
    st.markdown(
        f"#### From **{RESULT.score}** to **{CONDITIONAL_THRESHOLD}**, in point-optimal order"
    )
    st.caption(
        "Deductions are independent, so highest-value-first is the mathematically "
        "optimal order by points. Real-world effort varies — treat this as the "
        "negotiation-ready draft of your remediation plan."
    )
    steps = fastest_path(st.session_state.assessment, CAT)
    if not steps:
        st.success("Already at or above the threshold on every measure. 🎉")
    else:
        pdf_rows = []
        for i, s in enumerate(steps, 1):
            c = BY_ID[s["id"]]
            pdf_rows.append({
                "Step": i,
                "Control": s["id"],
                "What": c["short_title"],
                "Points": ("required" if s["required_first"] else f'+{s["gain"]}'),
                "Score after": s["score_after"],
            })
        st.dataframe(pd.DataFrame(pdf_rows), hide_index=True, use_container_width=True)
        last = steps[-1]
        if last["reaches_target"]:
            n = len([s for s in steps if not s["required_first"]])
            st.success(
                f"**{n} controls** stand between this organization and the "
                f"{CONDITIONAL_THRESHOLD}-point threshold — projected score "
                f"**{last['score_after']}** once complete."
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
        rows = []
        for cid, p in sorted(st.session_state.poam.items()):
            c = BY_ID[cid]
            tgt = date.fromisoformat(p["target_date"])
            rows.append({
                "Control": cid,
                "Requirement (short)": c["short_title"],
                "Points at stake": RESULT.per_control.get(cid, 0),
                "Target date": tgt.isoformat(),
                "Days remaining": (tgt - date.today()).days,
            })
        pdf = pd.DataFrame(rows)
        st.dataframe(pdf, hide_index=True, use_container_width=True)
        buf = io.StringIO()
        pdf.to_csv(buf, index=False)
        st.download_button("⬇️ Download POA&M (CSV)", buf.getvalue(),
                           file_name="poam.csv", mime="text/csv")

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
        f"- **{CONDITIONAL_THRESHOLD}** = 80% of 110, the CMMC Level 2 "
        "conditional-status minimum."
    )
    st.markdown("#### Data provenance")
    st.markdown(
        f"Control weights transcribed **{META['transcribed']}** from *{META['source']}*. "
        "Build-time validation asserts the exact published distribution "
        "(44 × 5-pt incl. two 5/3 specials, 14 × 3-pt, 51 × 1-pt, 1 × NA) and the "
        "−203 floor, so the data cannot silently drift from the methodology."
    )
    st.warning(
        "This workspace is a self-assessment aid. It is not legal advice, not a "
        "certification, and not a substitute for the official *NIST SP 800-171 "
        "DoD Assessment Methodology* or 32 CFR Part 170. Verify results against "
        "the official documents before posting a score to SPRS.",
        icon="⚖️",
    )
