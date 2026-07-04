"""Build data/controls.json and data/sample_assessment.json.

Source of truth: NIST SP 800-171 DoD Assessment Methodology, Version 1.2.1
(June 24, 2020), Annex A. Weights transcribed 2026-07-04 from the Annex A
scoring template (via CMMC Toolkit Wiki mirror of the official document).
Requirement text is NIST SP 800-171 Rev 2 language (U.S. Government work,
public domain).

Validation enforced on every build:
  - exactly 110 controls, correct per-family counts
  - weight distribution: 44 five-point rows (incl. two 5/3 specials),
    14 three-point, 51 one-point, 1 NA (3.12.4 System Security Plan)
  - maximum total deduction 313  ->  floor score of exactly -203

Run:  python scripts/build_catalog.py [--check]
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

FAMILIES = {
    "3.1": "Access Control",
    "3.2": "Awareness & Training",
    "3.3": "Audit & Accountability",
    "3.4": "Configuration Management",
    "3.5": "Identification & Authentication",
    "3.6": "Incident Response",
    "3.7": "Maintenance",
    "3.8": "Media Protection",
    "3.9": "Personnel Security",
    "3.10": "Physical Protection",
    "3.11": "Risk Assessment",
    "3.12": "Security Assessment",
    "3.13": "System & Communications Protection",
    "3.14": "System & Information Integrity",
}

EXPECTED_FAMILY_COUNTS = {
    "3.1": 22, "3.2": 3, "3.3": 9, "3.4": 9, "3.5": 11, "3.6": 3, "3.7": 6,
    "3.8": 9, "3.9": 2, "3.10": 6, "3.11": 3, "3.12": 4, "3.13": 16, "3.14": 7,
}

# Controls where Annex A says: do not subtract points if the capability
# (remote access / wireless / mobile devices) is not permitted at all.
CONDITIONAL_NA = {"3.1.12", "3.1.13", "3.1.16", "3.1.17", "3.1.18"}

# (id, weight, short_title, requirement_text)
# weight: 5 | 3 | 1 | "5/3" (partial-credit specials) | "NA" (3.12.4 SSP)
CONTROLS = [
    # ---- 3.1 Access Control (22) ----
    ("3.1.1", 5, "Limit access to authorized users",
     "Limit system access to authorized users, processes acting on behalf of authorized users, and devices (including other systems)."),
    ("3.1.2", 5, "Limit access to permitted functions",
     "Limit system access to the types of transactions and functions that authorized users are permitted to execute."),
    ("3.1.3", 1, "Control CUI flow",
     "Control the flow of CUI in accordance with approved authorizations."),
    ("3.1.4", 1, "Separation of duties",
     "Separate the duties of individuals to reduce the risk of malevolent activity without collusion."),
    ("3.1.5", 3, "Least privilege",
     "Employ the principle of least privilege, including for specific security functions and privileged accounts."),
    ("3.1.6", 1, "Non-privileged accounts for daily work",
     "Use non-privileged accounts or roles when accessing nonsecurity functions."),
    ("3.1.7", 1, "Block & log privileged functions",
     "Prevent non-privileged users from executing privileged functions and capture the execution of such functions in audit logs."),
    ("3.1.8", 1, "Limit failed logons",
     "Limit unsuccessful logon attempts."),
    ("3.1.9", 1, "Privacy & security notices",
     "Provide privacy and security notices consistent with applicable CUI rules."),
    ("3.1.10", 1, "Session lock",
     "Use session lock with pattern-hiding displays to prevent access and viewing of data after a period of inactivity."),
    ("3.1.11", 1, "Auto-terminate sessions",
     "Terminate (automatically) a user session after a defined condition."),
    ("3.1.12", 5, "Monitor & control remote access",
     "Monitor and control remote access sessions."),
    ("3.1.13", 5, "Encrypt remote access sessions",
     "Employ cryptographic mechanisms to protect the confidentiality of remote access sessions."),
    ("3.1.14", 1, "Route remote access via control points",
     "Route remote access via managed access control points."),
    ("3.1.15", 1, "Authorize remote privileged commands",
     "Authorize remote execution of privileged commands and remote access to security-relevant information."),
    ("3.1.16", 5, "Authorize wireless access",
     "Authorize wireless access prior to allowing such connections."),
    ("3.1.17", 5, "Protect wireless (authn + encryption)",
     "Protect wireless access using authentication and encryption."),
    ("3.1.18", 5, "Control mobile device connections",
     "Control connection of mobile devices."),
    ("3.1.19", 3, "Encrypt CUI on mobile devices",
     "Encrypt CUI on mobile devices and mobile computing platforms."),
    ("3.1.20", 1, "Control connections to external systems",
     "Verify and control/limit connections to and use of external systems."),
    ("3.1.21", 1, "Limit portable storage on external systems",
     "Limit use of portable storage devices on external systems."),
    ("3.1.22", 1, "Control CUI on public systems",
     "Control CUI posted or processed on publicly accessible systems."),
    # ---- 3.2 Awareness & Training (3) ----
    ("3.2.1", 5, "Security awareness for all users",
     "Ensure that managers, systems administrators, and users of organizational systems are made aware of the security risks associated with their activities and of the applicable policies, standards, and procedures related to the security of those systems."),
    ("3.2.2", 5, "Role-based security training",
     "Ensure that personnel are trained to carry out their assigned information security-related duties and responsibilities."),
    ("3.2.3", 1, "Insider-threat awareness",
     "Provide security awareness training on recognizing and reporting potential indicators of insider threat."),
    # ---- 3.3 Audit & Accountability (9) ----
    ("3.3.1", 5, "Create & retain audit logs",
     "Create and retain system audit logs and records to the extent needed to enable the monitoring, analysis, investigation, and reporting of unlawful or unauthorized system activity."),
    ("3.3.2", 3, "Trace actions to individual users",
     "Ensure that the actions of individual system users can be uniquely traced to those users, so they can be held accountable for their actions."),
    ("3.3.3", 1, "Review & update logged events",
     "Review and update logged events."),
    ("3.3.4", 1, "Alert on audit logging failure",
     "Alert in the event of an audit logging process failure."),
    ("3.3.5", 5, "Correlate audit review & response",
     "Correlate audit record review, analysis, and reporting processes for investigation and response to indications of unlawful, unauthorized, suspicious, or unusual activity."),
    ("3.3.6", 1, "Audit reduction & reporting",
     "Provide audit record reduction and report generation to support on-demand analysis and reporting."),
    ("3.3.7", 1, "Synchronized time stamps",
     "Provide a system capability that compares and synchronizes internal system clocks with an authoritative source to generate time stamps for audit records."),
    ("3.3.8", 1, "Protect audit info & tools",
     "Protect audit information and audit logging tools from unauthorized access, modification, and deletion."),
    ("3.3.9", 1, "Limit audit management to few admins",
     "Limit management of audit logging functionality to a subset of privileged users."),
    # ---- 3.4 Configuration Management (9) ----
    ("3.4.1", 5, "Baseline configurations & inventories",
     "Establish and maintain baseline configurations and inventories of organizational systems (including hardware, software, firmware, and documentation) throughout the respective system development life cycles."),
    ("3.4.2", 5, "Enforce security configuration settings",
     "Establish and enforce security configuration settings for information technology products employed in organizational systems."),
    ("3.4.3", 1, "Track & approve system changes",
     "Track, review, approve or disapprove, and log changes to organizational systems."),
    ("3.4.4", 1, "Analyze security impact of changes",
     "Analyze the security impact of changes prior to implementation."),
    ("3.4.5", 5, "Access restrictions for changes",
     "Define, document, approve, and enforce physical and logical access restrictions associated with changes to organizational systems."),
    ("3.4.6", 5, "Least functionality",
     "Employ the principle of least functionality by configuring organizational systems to provide only essential capabilities."),
    ("3.4.7", 5, "Restrict nonessential programs/ports/services",
     "Restrict, disable, or prevent the use of nonessential programs, functions, ports, protocols, and services."),
    ("3.4.8", 5, "Application allowlisting / denylisting",
     "Apply deny-by-exception (blacklisting) policy to prevent the use of unauthorized software or deny-all, permit-by-exception (whitelisting) policy to allow the execution of authorized software."),
    ("3.4.9", 1, "Control user-installed software",
     "Control and monitor user-installed software."),
    # ---- 3.5 Identification & Authentication (11) ----
    ("3.5.1", 5, "Identify users, processes, devices",
     "Identify system users, processes acting on behalf of users, and devices."),
    ("3.5.2", 5, "Authenticate before access",
     "Authenticate (or verify) the identities of users, processes, or devices, as a prerequisite to allowing access to organizational systems."),
    ("3.5.3", "5/3", "Multifactor authentication (MFA)",
     "Use multifactor authentication for local and network access to privileged accounts and for network access to non-privileged accounts."),
    ("3.5.4", 1, "Replay-resistant authentication",
     "Employ replay-resistant authentication mechanisms for network access to privileged and non-privileged accounts."),
    ("3.5.5", 1, "Prevent identifier reuse",
     "Prevent reuse of identifiers for a defined period."),
    ("3.5.6", 1, "Disable inactive identifiers",
     "Disable identifiers after a defined period of inactivity."),
    ("3.5.7", 1, "Password complexity",
     "Enforce a minimum password complexity and change of characters when new passwords are created."),
    ("3.5.8", 1, "Prohibit password reuse",
     "Prohibit password reuse for a specified number of generations."),
    ("3.5.9", 1, "Temporary passwords",
     "Allow temporary password use for system logons with an immediate change to a permanent password."),
    ("3.5.10", 5, "Cryptographically protect passwords",
     "Store and transmit only cryptographically-protected passwords."),
    ("3.5.11", 1, "Obscure authentication feedback",
     "Obscure feedback of authentication information."),
    # ---- 3.6 Incident Response (3) ----
    ("3.6.1", 5, "Operational incident-handling capability",
     "Establish an operational incident-handling capability for organizational systems that includes preparation, detection, analysis, containment, recovery, and user response activities."),
    ("3.6.2", 5, "Track, document & report incidents",
     "Track, document, and report incidents to designated officials and/or authorities both internal and external to the organization."),
    ("3.6.3", 1, "Test incident response",
     "Test the organizational incident response capability."),
    # ---- 3.7 Maintenance (6) ----
    ("3.7.1", 3, "Perform system maintenance",
     "Perform maintenance on organizational systems."),
    ("3.7.2", 5, "Control maintenance tools & personnel",
     "Provide controls on the tools, techniques, mechanisms, and personnel used to conduct system maintenance."),
    ("3.7.3", 1, "Sanitize equipment for off-site maintenance",
     "Ensure equipment removed for off-site maintenance is sanitized of any CUI."),
    ("3.7.4", 3, "Check maintenance media for malware",
     "Check media containing diagnostic and test programs for malicious code before the media are used in organizational systems."),
    ("3.7.5", 5, "MFA for nonlocal maintenance",
     "Require multifactor authentication to establish nonlocal maintenance sessions via external network connections and terminate such connections when nonlocal maintenance is complete."),
    ("3.7.6", 1, "Supervise unescorted maintenance personnel",
     "Supervise the maintenance activities of maintenance personnel without required access authorization."),
    # ---- 3.8 Media Protection (9) ----
    ("3.8.1", 3, "Protect media containing CUI",
     "Protect (i.e., physically control and securely store) system media containing CUI, both paper and digital."),
    ("3.8.2", 3, "Limit access to CUI on media",
     "Limit access to CUI on system media to authorized users."),
    ("3.8.3", 5, "Sanitize media before disposal/reuse",
     "Sanitize or destroy system media containing CUI before disposal or release for reuse."),
    ("3.8.4", 1, "Mark media with CUI markings",
     "Mark media with necessary CUI markings and distribution limitations."),
    ("3.8.5", 1, "Control media during transport",
     "Control access to media containing CUI and maintain accountability for media during transport outside of controlled areas."),
    ("3.8.6", 1, "Encrypt CUI on media in transport",
     "Implement cryptographic mechanisms to protect the confidentiality of CUI stored on digital media during transport unless otherwise protected by alternative physical safeguards."),
    ("3.8.7", 5, "Control removable media",
     "Control the use of removable media on system components."),
    ("3.8.8", 3, "Prohibit unowned portable storage",
     "Prohibit the use of portable storage devices when such devices have no identifiable owner."),
    ("3.8.9", 1, "Protect backups of CUI",
     "Protect the confidentiality of backup CUI at storage locations."),
    # ---- 3.9 Personnel Security (2) ----
    ("3.9.1", 3, "Screen individuals before access",
     "Screen individuals prior to authorizing access to organizational systems containing CUI."),
    ("3.9.2", 5, "Protect CUI during personnel actions",
     "Ensure that organizational systems containing CUI are protected during and after personnel actions such as terminations and transfers."),
    # ---- 3.10 Physical Protection (6) ----
    ("3.10.1", 5, "Limit physical access",
     "Limit physical access to organizational systems, equipment, and the respective operating environments to authorized individuals."),
    ("3.10.2", 5, "Protect & monitor the facility",
     "Protect and monitor the physical facility and support infrastructure for organizational systems."),
    ("3.10.3", 1, "Escort & monitor visitors",
     "Escort visitors and monitor visitor activity."),
    ("3.10.4", 1, "Physical access audit logs",
     "Maintain audit logs of physical access."),
    ("3.10.5", 1, "Manage physical access devices",
     "Control and manage physical access devices."),
    ("3.10.6", 1, "Safeguard CUI at alternate work sites",
     "Enforce safeguarding measures for CUI at alternate work sites."),
    # ---- 3.11 Risk Assessment (3) ----
    ("3.11.1", 3, "Periodic risk assessments",
     "Periodically assess the risk to organizational operations (including mission, functions, image, or reputation), organizational assets, and individuals, resulting from the operation of organizational systems and the associated processing, storage, or transmission of CUI."),
    ("3.11.2", 5, "Vulnerability scanning",
     "Scan for vulnerabilities in organizational systems and applications periodically and when new vulnerabilities affecting those systems and applications are identified."),
    ("3.11.3", 1, "Remediate vulnerabilities",
     "Remediate vulnerabilities in accordance with risk assessments."),
    # ---- 3.12 Security Assessment (4) ----
    ("3.12.1", 5, "Periodic security control assessment",
     "Periodically assess the security controls in organizational systems to determine if the controls are effective in their application."),
    ("3.12.2", 3, "Plans of action (POA&M)",
     "Develop and implement plans of action designed to correct deficiencies and reduce or eliminate vulnerabilities in organizational systems."),
    ("3.12.3", 5, "Continuous control monitoring",
     "Monitor security controls on an ongoing basis to ensure the continued effectiveness of the controls."),
    ("3.12.4", "NA", "System Security Plan (SSP)",
     "Develop, document, and periodically update system security plans that describe system boundaries, system environments of operation, how security requirements are implemented, and the relationships with or connections to other systems."),
    # ---- 3.13 System & Communications Protection (16) ----
    ("3.13.1", 5, "Monitor & protect boundary communications",
     "Monitor, control, and protect communications (i.e., information transmitted or received by organizational systems) at the external boundaries and key internal boundaries of organizational systems."),
    ("3.13.2", 5, "Secure architecture & engineering",
     "Employ architectural designs, software development techniques, and systems engineering principles that promote effective information security within organizational systems."),
    ("3.13.3", 1, "Separate user & admin functionality",
     "Separate user functionality from system management functionality."),
    ("3.13.4", 1, "Prevent transfer via shared resources",
     "Prevent unauthorized and unintended information transfer via shared system resources."),
    ("3.13.5", 5, "DMZ / subnetworks for public components",
     "Implement subnetworks for publicly accessible system components that are physically or logically separated from internal networks."),
    ("3.13.6", 5, "Deny by default, allow by exception",
     "Deny network communications traffic by default and allow network communications traffic by exception (i.e., deny all, permit by exception)."),
    ("3.13.7", 1, "Prevent split tunneling",
     "Prevent remote devices from simultaneously establishing non-remote connections with organizational systems and communicating via some other connection to resources in external networks (i.e., split tunneling)."),
    ("3.13.8", 3, "Encrypt CUI in transit",
     "Implement cryptographic mechanisms to prevent unauthorized disclosure of CUI during transmission unless otherwise protected by alternative physical safeguards."),
    ("3.13.9", 1, "Terminate idle network connections",
     "Terminate network connections associated with communications sessions at the end of the sessions or after a defined period of inactivity."),
    ("3.13.10", 1, "Cryptographic key management",
     "Establish and manage cryptographic keys for cryptography employed in organizational systems."),
    ("3.13.11", "5/3", "FIPS-validated cryptography",
     "Employ FIPS-validated cryptography when used to protect the confidentiality of CUI."),
    ("3.13.12", 1, "Control collaborative devices",
     "Prohibit remote activation of collaborative computing devices and provide indication of devices in use to users present at the device."),
    ("3.13.13", 1, "Control mobile code",
     "Control and monitor the use of mobile code."),
    ("3.13.14", 1, "Control VoIP",
     "Control and monitor the use of Voice over Internet Protocol (VoIP) technologies."),
    ("3.13.15", 5, "Protect session authenticity",
     "Protect the authenticity of communications sessions."),
    ("3.13.16", 1, "Protect CUI at rest",
     "Protect the confidentiality of CUI at rest."),
    # ---- 3.14 System & Information Integrity (7) ----
    ("3.14.1", 5, "Identify & correct system flaws (patching)",
     "Identify, report, and correct system flaws in a timely manner."),
    ("3.14.2", 5, "Malicious code protection",
     "Provide protection from malicious code at designated locations within organizational systems."),
    ("3.14.3", 5, "Monitor security alerts & act",
     "Monitor system security alerts and advisories and take action in response."),
    ("3.14.4", 5, "Update malware protection",
     "Update malicious code protection mechanisms when new releases are available."),
    ("3.14.5", 3, "Periodic & real-time scans",
     "Perform periodic scans of organizational systems and real-time scans of files from external sources as files are downloaded, opened, or executed."),
    ("3.14.6", 5, "Monitor traffic for attacks",
     "Monitor organizational systems, including inbound and outbound communications traffic, to detect attacks and indicators of potential attacks."),
    ("3.14.7", 3, "Identify unauthorized use",
     "Identify unauthorized use of organizational systems."),
]

# Plain-English guidance for the highest-impact controls (demo tier).
# Voice: written for the IT manager at a 25-person shop, not for an auditor.
GUIDANCE = {
    "3.1.1": {
        "plain": "Every account on your systems belongs to a specific, approved person — no shared logins, no ghosts. If you can't say who 'shopfloor2' is, this control isn't met.",
        "evidence": "User list export from Microsoft 365 / Active Directory with a quarterly review sign-off; onboarding/offboarding checklist.",
        "quick_win": "Export your user list today and disable every account you can't match to a current employee.",
    },
    "3.3.1": {
        "plain": "Your systems keep records of who did what, when — and you keep those records long enough to investigate an incident months later. Default 30-day retention usually isn't enough.",
        "evidence": "Screenshot of audit log settings and retention period; a sample log pull for one user.",
        "quick_win": "Turn on Microsoft 365 unified audit logging and extend retention as far as your license allows.",
    },
    "3.4.1": {
        "plain": "A written inventory of every computer, server, and piece of software you own, plus a documented 'standard build' for how a new machine gets set up.",
        "evidence": "Asset inventory (export from Intune/RMM counts); a one-page standard configuration document.",
        "quick_win": "Export the device list from whatever management tool you have — that's the skeleton of your inventory.",
    },
    "3.4.2": {
        "plain": "You don't run machines on factory defaults — there's a hardening checklist (disable what you don't use, enforce screen lock, etc.) and it's actually applied.",
        "evidence": "Group Policy / Intune configuration profiles; a hardening checklist referencing a benchmark like CIS.",
        "quick_win": "Adopt a published small-business hardening baseline instead of writing your own from scratch.",
    },
    "3.5.3": {
        "plain": "Multifactor authentication for everyone — not just email. Partial credit exists: MFA for admins and remote users only loses 3 points instead of 5. Full credit requires the general workforce too.",
        "evidence": "MFA status export from your identity provider showing per-user enforcement.",
        "quick_win": "Enforce MFA for admin and remote accounts this week (that alone moves you from −5 to −3), then roll out to everyone.",
    },
    "3.6.1": {
        "plain": "When something bad happens, you have a written plan: who's in charge, who you call, how you contain it, how you recover. A plan that exists only in someone's head scores zero.",
        "evidence": "A written incident response plan with named roles; notes from at least one walkthrough or tabletop exercise.",
        "quick_win": "Draft a two-page IR plan from a free template and put real names and phone numbers in it.",
    },
    "3.8.3": {
        "plain": "Before a computer, drive, or copier leaves your building — sold, recycled, returned off lease — the data on it is wiped or the drive is destroyed, and you keep a record.",
        "evidence": "Wipe/destruction log; certificates of destruction from your recycler.",
        "quick_win": "Start a simple disposal log today; ask your recycler for certificates going forward.",
    },
    "3.8.7": {
        "plain": "USB sticks and external drives don't just get plugged in freely. You either block removable media by policy and technical control, or you control which specific devices are allowed.",
        "evidence": "Endpoint policy screenshot showing removable-media restrictions; written removable media policy.",
        "quick_win": "If you can't manage USB devices yet, block them outright — blocking fully satisfies this control.",
    },
    "3.11.2": {
        "plain": "Something regularly scans your systems for known security holes, and you look at the results. 'Our IT guy keeps an eye on things' is not a scan.",
        "evidence": "Recent vulnerability scan reports with dates; a note on scan frequency.",
        "quick_win": "Microsoft Defender's built-in vulnerability management or a free scanner tier gets you a first real report this week.",
    },
    "3.12.4": {
        "plain": "The System Security Plan is the master document describing your environment and how each requirement is met. Under the DoD methodology, without an SSP there is no score at all — the assessment cannot be completed.",
        "evidence": "The SSP itself, with a revision date within the last year.",
        "quick_win": "Start from a free SSP template and fill in your real environment — an honest draft beats a blank page in every scenario.",
    },
    "3.13.8": {
        "plain": "CUI moving over networks is encrypted — TLS for web and email paths, VPN for site-to-site. If a file with CUI travels in the clear, this fails.",
        "evidence": "Configuration screenshots showing TLS enforcement / VPN settings for paths that carry CUI.",
        "quick_win": "Force TLS on your email connectors and require the VPN for any remote path that touches CUI.",
    },
    "3.13.11": {
        "plain": "Where encryption protects CUI, the cryptographic module must be FIPS-validated — using a strong algorithm isn't enough; the module needs a CMVP certificate. Partial credit: encryption in use but not FIPS-validated loses 3 points instead of 5.",
        "evidence": "List of encryption in use with CMVP certificate numbers (e.g., BitLocker in FIPS mode).",
        "quick_win": "Inventory where CUI is encrypted today, then check each product's FIPS validation status on the NIST CMVP database.",
    },
    "3.14.1": {
        "plain": "Security patches get applied on a schedule with deadlines — not 'when we get around to it.' You can show when a given patch landed.",
        "evidence": "Patch compliance report from your update tool; written patching cadence with deadlines.",
        "quick_win": "Set automatic updates with a defined maximum deferral and export your first compliance report.",
    },
    "3.14.2": {
        "plain": "Anti-malware runs on every machine, it's centrally visible, and nobody can quietly turn it off.",
        "evidence": "Coverage report from your AV/EDR console showing all endpoints protected and current.",
        "quick_win": "Pull the coverage report and chase the stragglers — the gap machines are the whole risk.",
    },
}

# Sample company: THE CENTERPIECE — scores exactly 89 yet is NOT conditionally
# ready. It teaches the whole lesson on one screen: crossing 88 is necessary but
# not sufficient. Open items sum to -21 (110-21=89), SSP present (costs 0):
#   3.4.8 / 3.13.6 / 3.14.6  not_implemented  -5 each  -> NOT POA&M-eligible (5-pt)
#   3.13.11                  partial_alt      -3       -> POA&M-eligible (sole exception)
#   3.1.20                   not_implemented  -1       -> NOT eligible (one of the six named)
#   3.3.4 / 3.6.3            not_implemented  -1 each  -> POA&M-eligible
# Result: score_ok(89>=88) & ssp_ok, but 4 blockers -> Conditional INELIGIBLE.
SAMPLE_NOT_IMPLEMENTED = [
    "3.4.8", "3.13.6", "3.14.6",   # three 5-pt mandatory blockers
    "3.1.20",                        # excluded 1-pt (never POA&M-able) blocker
    "3.3.4", "3.6.3",               # eligible 1-pt gaps
]
SAMPLE_PARTIAL = ["3.13.11"]  # encryption in use but not FIPS-validated (eligible at -3)
SAMPLE_POAM = {
    "3.3.4": "2026-08-31",
    "3.6.3": "2026-09-30",
    "3.13.11": "2026-10-15",
}
# Evidence register rows (metadata only — NO files stored). Shape matches the
# Phase-1 evidence-register schema consumed by app.py / the binder.
SAMPLE_EVIDENCE = {
    "3.10.1": [{
        "title": "Badge access policy + Q2 facility log",
        "owner": "Facilities Lead",
        "location_uri": "SharePoint > Compliance > Physical",
        "doc_status": "final", "impl_status": "demonstrates_operation",
        "review_status": "reviewed",
    }],
    "3.14.2": [{
        "title": "Defender for Endpoint coverage report",
        "owner": "IT Manager",
        "location_uri": "Defender console > Reports",
        "doc_status": "final", "impl_status": "demonstrates_operation",
        "review_status": "unreviewed",
    }],
    "3.4.8": [{
        "title": "Allowlisting rollout plan (draft)",
        "owner": "IT Manager",
        "location_uri": "internal wiki > projects",
        "doc_status": "draft", "impl_status": "documented_only",
        "review_status": "unreviewed",
    }],
}


def _draft_guidance(short, req):
    """Conservative, requirement-grounded DRAFT guidance for controls not yet given
    curated, expert-reviewed text. Deliberately generic — it paraphrases the
    requirement and asks for operating evidence, so it never fabricates specifics.
    Marked reviewed=False; the UI badges it 'pending expert review'."""
    return {
        "plain": (f"In plain terms: {req} The test isn't whether it's written down — "
                  "it's whether it actually happens and you can show it."),
        "evidence": ("A policy or configuration establishing this requirement, plus a "
                     "record that shows it operating (a screenshot, export, or log)."),
        "quick_win": (f"Name who owns “{short.lower()}” and capture one piece "
                      "of evidence that it is operating today."),
        "reviewed": False,
    }


def build():
    controls = []
    for cid, weight, short, req in CONTROLS:
        fam = cid.rsplit(".", 1)[0]
        special = None
        if cid == "3.5.3":
            special = "mfa"
        elif cid == "3.13.11":
            special = "fips"
        elif cid == "3.12.4":
            special = "ssp"
        if cid in GUIDANCE:
            guidance = {**GUIDANCE[cid], "reviewed": True}   # curated
        else:
            guidance = _draft_guidance(short, req)            # generated draft
        controls.append({
            "id": cid,
            "family": fam,
            "family_name": FAMILIES[fam],
            "weight": weight,
            "max_deduction": 5 if weight == "5/3" else (0 if weight == "NA" else weight),
            "special": special,
            "conditional_na": cid in CONDITIONAL_NA,
            "short_title": short,
            "requirement": req,
            "guidance": guidance,
        })
    return controls


def validate(controls):
    assert len(controls) == 110, f"expected 110 controls, got {len(controls)}"
    ids = [c["id"] for c in controls]
    assert len(set(ids)) == 110, "duplicate control ids"
    for fam, n in EXPECTED_FAMILY_COUNTS.items():
        got = sum(1 for c in controls if c["family"] == fam)
        assert got == n, f"family {fam}: expected {n}, got {got}"
    fives = [c for c in controls if c["weight"] == 5 or c["weight"] == "5/3"]
    threes = [c for c in controls if c["weight"] == 3]
    ones = [c for c in controls if c["weight"] == 1]
    nas = [c for c in controls if c["weight"] == "NA"]
    assert len(fives) == 44, f"expected 44 five-point rows, got {len(fives)}"
    assert len(threes) == 14, f"expected 14 three-point rows, got {len(threes)}"
    assert len(ones) == 51, f"expected 51 one-point rows, got {len(ones)}"
    assert len(nas) == 1 and nas[0]["id"] == "3.12.4", "3.12.4 must be the sole NA control"
    max_deduction = sum(c["max_deduction"] for c in controls)
    assert max_deduction == 313, f"max deduction must be 313, got {max_deduction}"
    floor = 110 - max_deduction
    assert floor == -203, f"floor must be -203, got {floor}"
    for cid in CONDITIONAL_NA:
        c = next(x for x in controls if x["id"] == cid)
        assert c["weight"] == 5, f"{cid} conditional-NA control should be 5-point"
    # Guidance coverage: every control must have non-empty plain/evidence/quick_win.
    reviewed = 0
    for c in controls:
        g = c.get("guidance")
        assert g, f"{c['id']}: missing guidance"
        for key in ("plain", "evidence", "quick_win"):
            assert g.get(key), f"{c['id']}: guidance '{key}' is empty"
        if g.get("reviewed"):
            reviewed += 1
    return {
        "fives": len(fives), "threes": len(threes), "ones": len(ones),
        "na": len(nas), "max_deduction": max_deduction, "floor": floor,
        "guidance_total": len(controls), "guidance_reviewed": reviewed,
    }


def validate_readiness(controls):
    """Assert the POA&M eligibility ruleset is consistent with the catalog and that
    the sample lands at the 89-but-not-ready verdict. Keeps the centerpiece and the
    32-CFR-170.21 rules from silently drifting."""
    import sys as _sys
    _sys.path.insert(0, str(ROOT))
    from logic.readiness import conditional_eligibility  # noqa: E402

    rules = json.loads((DATA / "poam_eligibility.json").read_text(encoding="utf-8"))
    by_id = {c["id"]: c for c in controls}

    excluded = rules["excluded_ids"]
    assert len(excluded) == 6, f"expected 6 excluded ids, got {len(excluded)}"
    for cid in excluded:
        assert cid in by_id, f"excluded id {cid} not in catalog"
    # Five of the six are 1-point; 3.12.4 is the NA (SSP) row.
    excl_ones = [c for c in controls if c["id"] in excluded and c["weight"] == 1]
    assert len(excl_ones) == 5, f"expected 5 one-point excluded controls, got {len(excl_ones)}"
    assert "3.12.4" in excluded, "3.12.4 (SSP) must be on the never-eligible list"
    # Default-eligible 1-point set = 51 one-pointers minus the 5 excluded = 46.
    ones = sum(1 for c in controls if c["weight"] == 1)
    assert ones - len(excl_ones) == 46, "default-eligible 1-pt set must be 46"
    # The sole partial-credit exception.
    assert "3.13.11" in rules["exceptions"], "3.13.11 encryption exception missing"
    assert rules["exceptions"]["3.13.11"]["allowed_status"] == "partial_alt"

    # The centerpiece: sample scores exactly 89 and is NOT conditionally eligible.
    sample = build_sample(controls)
    elig = conditional_eligibility(sample["statuses"], controls, rules)
    assert elig.score == 89, f"sample must score 89, got {elig.score}"
    assert elig.score_ok and elig.ssp_ok, "sample must clear 88 and have an SSP"
    assert not elig.eligible, "sample must be NOT conditionally eligible (the whole point)"
    assert set(elig.blocking_ids) == {"3.4.8", "3.13.6", "3.14.6", "3.1.20"}, \
        f"unexpected blockers: {elig.blocking_ids}"
    return {
        "excluded": len(excluded), "default_eligible_ones": ones - len(excl_ones),
        "sample_score": elig.score, "sample_eligible": elig.eligible,
        "sample_blockers": elig.blocking_ids,
    }


def build_sample(controls):
    statuses = {}
    for c in controls:
        cid = c["id"]
        if cid in SAMPLE_PARTIAL:
            statuses[cid] = "partial_alt"
        elif cid in SAMPLE_NOT_IMPLEMENTED:
            statuses[cid] = "not_implemented"
        else:
            statuses[cid] = "implemented"
    return {
        "company": "Gulf Coast Precision Machining (sample data)",
        "statuses": statuses,
        "poam": {cid: {"target_date": d} for cid, d in SAMPLE_POAM.items()},
        "evidence": SAMPLE_EVIDENCE,
    }


def main():
    controls = build()
    stats = validate(controls)
    DATA.mkdir(exist_ok=True)
    meta = {
        "source": "NIST SP 800-171 DoD Assessment Methodology v1.2.1 (2020-06-24), Annex A",
        "transcribed": "2026-07-04",
        "note": "Verify against the official document before customer use.",
        "stats": stats,
    }
    (DATA / "controls.json").write_text(
        json.dumps({"meta": meta, "controls": controls}, indent=1), encoding="utf-8")
    (DATA / "sample_assessment.json").write_text(
        json.dumps(build_sample(controls), indent=1), encoding="utf-8")
    readiness = validate_readiness(controls)
    print(f"OK  110 controls | 5pt:{stats['fives']}  3pt:{stats['threes']}  "
          f"1pt:{stats['ones']}  NA:{stats['na']} | max deduction {stats['max_deduction']} "
          f"-> floor {stats['floor']}")
    print(f"OK  POA&M rules: {readiness['excluded']} excluded, "
          f"{readiness['default_eligible_ones']} default-eligible 1-pt | "
          f"sample score {readiness['sample_score']} -> eligible={readiness['sample_eligible']} "
          f"(blockers: {', '.join(readiness['sample_blockers'])})")


if __name__ == "__main__":
    if "--check" in sys.argv:
        controls = build()
        stats = validate(controls)
        readiness = validate_readiness(controls)
        print(json.dumps({**stats, **readiness}, indent=2))
    else:
        main()
