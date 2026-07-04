# 🛡️ CMMC Vault — NIST SP 800-171 Self-Assessment Workspace (demo)

Your entire 800-171 self-assessment in one workspace built for a 20-person
shop: the 110-control checklist, live SPRS score, plain-English guidance,
evidence tracking, POA&M with export — and a point-optimal **fastest path
to 88** (the CMMC Level 2 conditional-status threshold).

**Demo build:** session-only. No accounts, nothing stored server-side.
Every visitor starts fresh; the *Load sample* button seeds a realistic
machine shop scoring **46** with a 9-step path past 88.

---

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy live (Streamlit Community Cloud, ~20 minutes)

1. Push this folder to a GitHub repo (public or private).
2. Go to **share.streamlit.io** → *Create app* → pick the repo/branch,
   main file `app.py` → **Deploy**.
3. You get a public URL like `cmmc-vault.streamlit.app`. Rename the
   subdomain in the app's settings.
4. Done — send the link, or run it on your phone in the parking lot of an
   APEX Accelerator workshop.

No secrets or environment variables are needed for the demo build.

## The 60-second demo script

1. Sidebar → **Load sample**. "This is a 28-person machine shop that thinks
   it's in decent shape."
2. **Dashboard**: score **46**. "This is the number a prime — and DoD — sees
   in SPRS. No score in SPRS, no award."
3. **Fastest path to 88** tab: "Nine controls. That's the whole conversation
   between you and eligibility — in the order that pays fastest."
4. Open **3.5.3 MFA** in the Assessment tab: flip *Not implemented* →
   *Remote & privileged only* and watch the score move by exactly 3. "The
   tool knows the real DoD math, including the partial-credit rules most
   spreadsheets get wrong."
5. **POA&M** tab → download the CSV. "And this is what you hand your prime
   when they ask."

## Data provenance (the credibility story)

- Control weights transcribed **2026-07-04** from the *NIST SP 800-171 DoD
  Assessment Methodology, Version 1.2.1 (June 24, 2020), Annex A*
  (official PDF on acq.osd.mil; transcription via the CMMC Toolkit Wiki
  mirror of the same document).
- `scripts/build_catalog.py` **hard-asserts** the published structure on
  every build: 44 five-point rows (including the two 5/3 partial-credit
  specials 3.5.3 and 3.13.11), 14 three-point, 51 one-point, and 3.12.4
  (SSP) as the sole NA — max deduction 313, floor exactly **−203**. The
  data cannot silently drift from the methodology.
- Encoded nuances most spreadsheets miss:
  - **3.12.4 SSP** carries no point value; without an SSP the methodology
    says the assessment *cannot be completed* (the app shows a hard banner).
  - **3.1.12/13/16/17/18**: no deduction when remote/wireless/mobile access
    is not permitted at all (N/A status with a document-the-policy prompt).
  - POA&M items still score as *not implemented*; missing plans of action
    flip **3.12.2** itself to not implemented.
- Requirement text is NIST SP 800-171 Rev 2 language (U.S. Government work,
  public domain).
- **Before first customer demo:** spot-check `data/controls.json` against
  the official PDF (30 minutes), and run
  `python scripts/build_catalog.py --check`.

## Tests

```bash
python -m unittest discover tests -v   # 13 tests: floor, specials, N/A rules, path
```

## Deliberately NOT in the demo

Accounts/auth, server-side persistence (Supabase), real evidence file
storage, SSP document generation, Word/PDF audit-binder export, multi-user,
Level 2 C3PAO workflow, continuous monitoring. That's the pilot tier —
the demo's job is to make a shop owner say "what's my number?"

## Pilot roadmap (after 5 prepaid signups)

1. Supabase auth + persistence (evidence files to storage buckets)
2. Plain-English guidance for all 110 controls (14 shipped in demo)
3. Audit-binder export (docx/PDF: SSP skeleton + control matrix + evidence index)
4. Annual-affirmation reminder emails
5. MSP multi-tenant view

## Disclaimer

Self-assessment aid only — not legal advice, not a certification, not a
substitute for the official DoD Assessment Methodology or 32 CFR Part 170.
Verify results against official sources before posting scores to SPRS.
