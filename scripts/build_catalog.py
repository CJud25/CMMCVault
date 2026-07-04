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
    # ---- Access Control (3.1.2-3.1.22) — SME-reviewed batch (2026-07-04) ----
    "3.1.2": {
        "plain": "Having an account isn't enough — each person can only perform the transactions and functions their job needs. Roles and permissions, not everyone-an-admin. A shop-floor user shouldn't be able to change security settings or financial records.",
        "evidence": "A role-to-function matrix mapping job roles to permitted system actions; screenshots of group/role membership (M365/AD) showing least-function access; a periodic access review with sign-off.",
        "quick_win": "List your system/app roles and confirm no standard user has admin or cross-department functions they don't need — then remove the extras.",
    },
    "3.1.3": {
        "plain": "You control where CUI is allowed to move — which systems, people, and networks — and block the paths it shouldn't take (no CUI to personal email or a consumer cloud drive).",
        "evidence": "A data-flow diagram showing where CUI enters, is stored, and leaves; mail-flow / DLP rules restricting CUI destinations; a list of authorized flows.",
        "quick_win": "Write down the few places CUI actually lives and moves, then add one mail-flow or DLP rule blocking the most obvious wrong path (e.g., external auto-forwarding).",
    },
    "3.1.4": {
        "plain": "No single person should control a whole sensitive process end to end. Whoever requests a system change isn't the only one who approves it; whoever manages accounts isn't the sole reviewer of the logs — so one person can't act badly without a second noticing.",
        "evidence": "A duty-separation matrix or a documented example (request vs. approve vs. implement handled by different roles); evidence that admin and audit-review duties aren't the same single person.",
        "quick_win": "Pick your highest-risk system task (creating admin accounts, changing security configs) and require a different second person to approve or review it — and write down who does each part.",
    },
    "3.1.5": {
        "plain": "Everyone gets the minimum access to do their job and nothing extra. Admin rights only for people who truly need them. Fewer admins, tightly scoped — including for security functions.",
        "evidence": "A list of privileged/admin accounts each with a justification; evidence that local-admin rights are removed from standard user machines; a periodic privilege review.",
        "quick_win": "Pull your admin list today and cut it to the few who genuinely need it; remove local-admin from everyday user laptops.",
    },
    "3.1.6": {
        "plain": "Even your admins use a normal (non-admin) account for everyday work — email, browsing, documents — and switch to their admin account only for admin tasks. That way a phished admin session doesn't hand over the keys.",
        "evidence": "Evidence that admins have separate standard and privileged accounts; a policy requiring non-privileged accounts for routine work.",
        "quick_win": "Give each admin a second, standard account for daily email/web, and reserve the admin account for admin work only.",
    },
    "3.1.7": {
        "plain": "Regular users can't run admin-level functions, and whenever anyone does run a privileged function, it's recorded. Two parts: block it for non-admins, and log it when it happens.",
        "evidence": "Configuration showing standard users can't execute privileged functions; audit-log samples that capture privileged actions.",
        "quick_win": "Confirm standard users can't install software or change system settings, and that your audit logging captures admin actions (turn on unified/admin audit logging).",
    },
    "3.1.8": {
        "plain": "After a set number of wrong password tries, the account locks or slows down, so someone can't just keep guessing. A simple, standard setting.",
        "evidence": "An account-lockout policy screenshot (threshold and duration) from AD / Entra ID / Intune.",
        "quick_win": "Set an account-lockout threshold (commonly 5-10 attempts) in Entra ID/AD if it isn't already — it's a one-setting change.",
    },
    "3.1.9": {
        "plain": "Systems that handle CUI show a use/consent banner at login stating acceptable use, that activity may be monitored, and the applicable privacy/CUI-handling notice, consistent with applicable CUI rules.",
        "evidence": "A screenshot of the logon banner and the acceptable-use / privacy text it references.",
        "quick_win": "Add a login/consent banner (a Group Policy or Intune setting) with standard acceptable-use, monitoring, and privacy language.",
    },
    "3.1.10": {
        "plain": "Screens lock automatically after a few idle minutes and show a lock screen — not the work — so a walk-by can't read CUI on an unattended machine.",
        "evidence": "A policy/configuration setting the inactivity-lock timeout (e.g., 15 minutes) with a pattern-hiding lock screen, applied via GPO/Intune.",
        "quick_win": "Enforce an automatic screen lock (10-15 minutes) by policy across all machines.",
    },
    "3.1.11": {
        "plain": "Sessions end automatically under defined conditions — for example, sign-out after long inactivity or a maximum session length, especially for remote and web sessions. This is more than just locking the screen.",
        "evidence": "Configuration for session timeout/termination (VPN idle disconnect, web-app session timeout, Conditional Access sign-in frequency).",
        "quick_win": "Set an idle-disconnect on your VPN and a session timeout / sign-in frequency on your cloud apps.",
    },
    "3.1.12": {
        "plain": "All remote access into your environment goes through approved, monitored channels — you know who is connecting remotely and can see and manage those sessions. If you genuinely permit no remote access of any kind — no VPN, no remote desktop, and no reaching company systems/cloud from outside your offices — it may be marked N/A; but this is uncommon for shops using cloud email/apps, since reaching those from off-site is itself remote access. Document the basis in your SSP and the assessor must agree.",
        "evidence": "A list of approved remote-access methods (VPN, RMM); logs/monitoring of remote sessions; Conditional Access policies governing remote sign-in.",
        "quick_win": "Make sure remote access happens only through one approved, logged method (e.g., VPN with MFA) and turn on its connection logging.",
    },
    "3.1.13": {
        "plain": "Remote connections are encrypted in transit (e.g., VPN or TLS) so the session can't be read; for CUI the encryption should use FIPS-validated cryptography. Mark N/A only if you truly permit no remote access (see 3.1.12), you document it, and the assessor agrees.",
        "evidence": "VPN/TLS configuration showing encryption in use for remote paths, the protocol/cipher settings, and evidence the mechanism uses FIPS-validated cryptography (CMVP certificate / FIPS mode enabled).",
        "quick_win": "Confirm every remote-access path rides an encrypted tunnel (a modern VPN or TLS) and retire any plaintext remote protocol.",
    },
    "3.1.14": {
        "plain": "Remote users come in through a small number of controlled gateways (a VPN concentrator or managed access point) — not scattered direct connections to individual machines.",
        "evidence": "A network diagram showing remote access funneled through defined gateways; firewall rules that enforce it.",
        "quick_win": "Ensure remote access terminates at one managed gateway, and block direct inbound remote connections to workstations.",
    },
    "3.1.15": {
        "plain": "Doing admin-level work or reaching security-relevant information remotely requires explicit authorization — it isn't something any remote user can do by default.",
        "evidence": "A policy authorizing remote privileged actions; Conditional Access or privileged-access controls restricting remote admin; approval records.",
        "quick_win": "Restrict remote admin to specific authorized accounts and devices (Conditional Access), and document who is approved.",
    },
    "3.1.16": {
        "plain": "Wireless connections are approved before they're allowed — you decide which devices and users can use Wi-Fi; it isn't open. If you permit no wireless at all, mark N/A and document it.",
        "evidence": "A wireless authorization policy; a controlled SSID with access control (802.1X or a pre-authorized device list); a separated guest network.",
        "quick_win": "Lock corporate Wi-Fi to authorized devices/users (WPA2/3-Enterprise or a device allowlist) and split off any guest network.",
    },
    "3.1.17": {
        "plain": "Wi-Fi that touches your environment uses strong authentication and encryption (WPA2/WPA3-Enterprise) — not an open network or a weak shared password. Mark N/A only if no wireless is permitted.",
        "evidence": "Wireless configuration showing WPA2/WPA3-Enterprise (or equivalent) with authentication and encryption enabled, using FIPS-validated cryptographic modules where the wireless carries CUI.",
        "quick_win": "Move corporate Wi-Fi to WPA2/WPA3-Enterprise with per-user/device authentication; retire WEP/WPA-Personal for anything touching CUI.",
    },
    "3.1.18": {
        "plain": "Phones and tablets that connect to your systems are managed and controlled — you decide which devices connect and can enforce security on them. Mark N/A if no mobile devices are permitted to connect.",
        "evidence": "MDM/Intune enrollment showing managed mobile devices; Conditional Access requiring a compliant device.",
        "quick_win": "Require mobile devices to be enrolled and compliant (Intune) before they can reach email or company data.",
    },
    "3.1.19": {
        "plain": "If CUI can land on a phone, tablet, or laptop, that device's storage is encrypted, so a lost or stolen device doesn't leak data.",
        "evidence": "Encryption enforcement using FIPS-validated encryption (e.g., BitLocker XTS-AES in FIPS mode, or MDM-enforced device encryption) with a compliance report.",
        "quick_win": "Turn on and enforce device encryption (BitLocker / mobile device encryption) via Intune and pull a compliance report.",
    },
    "3.1.20": {
        "plain": "You verify and control how your systems connect to outside systems — partner networks, personal devices, third-party cloud — deciding which are allowed and what they can do. Note: this control can NOT be placed on a POA&M; it must be met at assessment.",
        "evidence": "A policy defining permitted external connections/services; firewall or Conditional Access limits enforcing it; an approved external-systems list.",
        "quick_win": "Write down which external systems and services are approved to connect, and block or restrict the rest — this one must be met, not deferred.",
    },
    "3.1.21": {
        "plain": "You limit using company USB and portable drives on outside or uncontrolled computers (and vice versa), where they could pick up malware or leak CUI.",
        "evidence": "A removable-media policy that addresses use on external systems; endpoint controls governing USB use.",
        "quick_win": "Add a policy line — and an endpoint control where possible — restricting company portable drives to managed machines only.",
    },
    "3.1.22": {
        "plain": "Nothing containing CUI ends up on publicly accessible systems — your website, social media, or public file shares — and someone reviews and authorizes what goes public. Note: this control can NOT be placed on a POA&M; it must be met at assessment.",
        "evidence": "A policy and review process for public postings; evidence of who authorizes website/social content; confirmation no CUI sits on public shares.",
        "quick_win": "Assign one person to review anything before it goes on the public website or social media, and confirm no CUI is on public shares — must be met, not deferred.",
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
    # ---- System & Communications Protection (3.13.x) — SME-reviewed batch (2026-07-04) ----
    "3.13.1": {
        "plain": "You have a controlled, monitored edge to your network — a real managed firewall at the internet boundary (and at key internal boundaries, like around wherever CUI lives) that controls and inspects what crosses. Not just the ISP's box on default settings.",
        "evidence": "Firewall configuration/ruleset at the boundary; evidence of boundary monitoring/logging (firewall logs, IDS/IPS); a network diagram marking the external and key internal boundaries.",
        "quick_win": "Confirm a managed firewall sits at your internet edge with logging on, and identify the boundary around wherever CUI lives so you can protect it specifically.",
    },
    "3.13.2": {
        "plain": "Security is built into how your systems are designed and set up — you follow recognized secure-design and hardening principles (segmentation, least functionality, defense in depth) rather than bolting security on afterward. For a small shop this is largely documenting that you follow a known baseline/reference architecture.",
        "evidence": "A documented system/security architecture, or a reference to the secure baseline you follow (e.g., CIS Benchmarks, vendor security baselines); evidence that changes consider security impact.",
        "quick_win": "Write a short architecture note describing how your network is segmented and which hardening baseline you follow — that's the core artifact assessors look for here.",
    },
    "3.13.3": {
        "plain": "The tools and interfaces used to administer systems are kept separate from the ones regular users use — admins manage systems through dedicated consoles and admin accounts, not from the same interface a standard user has.",
        "evidence": "Evidence that management interfaces are separate from user functionality (separate admin portals, a jump host, distinct admin accounts).",
        "quick_win": "Make sure system administration happens through dedicated admin consoles/accounts, not mixed into everyday user desktops.",
    },
    "3.13.4": {
        "plain": "Shared system resources (memory, temporary storage, scratch space) don't leak leftover data from one user or process to the next. For a small shop this is mostly a matter of running current, supported, patched operating systems, which clear resources between uses by default.",
        "evidence": "Evidence of supported/patched operating systems with default object-reuse protections in place; no shared scratch areas that expose residual data.",
        "quick_win": "Keep systems on current, supported, patched OS versions — object-reuse protection is built in; the real risk is unsupported or unpatched systems.",
    },
    "3.13.5": {
        "plain": "Anything the public can reach — a web server or a public-facing service — sits on a separate network segment (a DMZ) walled off from your internal network, so a compromise of the public thing doesn't hand over the inside.",
        "evidence": "A network diagram showing public-facing components in a separate subnet/DMZ; firewall rules isolating that segment from the internal network.",
        "quick_win": "If you host anything publicly reachable, put it on a separate subnet/VLAN with firewall rules blocking it from initiating connections into your internal network. If you host nothing public, document that.",
    },
    "3.13.6": {
        "plain": "Your firewall blocks all traffic by default and only allows what you've explicitly permitted — both inbound and, importantly, outbound. The opposite (allow-all, block-a-few) is the common weak default this control exists to fix.",
        "evidence": "A firewall ruleset ending in an explicit default-deny; a documented list of explicitly-permitted flows; evidence that outbound traffic is also restricted, not just inbound.",
        "quick_win": "Add an explicit default-deny at the end of your firewall rules and review outbound rules — most shops allow all outbound, which this control expects you to tighten.",
    },
    "3.13.7": {
        "plain": "When a device is connected to your network remotely (over VPN), it can't simultaneously bridge to the open internet in a way that routes around your protections — the VPN forces that device's traffic through your controls instead of out a second, uncontrolled path.",
        "evidence": "VPN configuration enforcing full-tunnel, or otherwise preventing split tunneling, for remote devices.",
        "quick_win": "Set your VPN to full-tunnel (or explicitly disable split tunneling) so remote sessions can't bridge your network to the open internet.",
    },
    "3.13.9": {
        "plain": "Network sessions get torn down when they end or after a period of inactivity — connections don't linger open indefinitely (VPN idle timeout, server and firewall session timeouts).",
        "evidence": "Configuration showing network/session idle timeouts (VPN, servers, firewall session tables).",
        "quick_win": "Set idle timeouts on your VPN and key network services so idle connections drop automatically.",
    },
    "3.13.10": {
        "plain": "The keys and certificates behind your encryption are managed properly — generated, stored, rotated, and retired securely — not left in default states or shared insecurely.",
        "evidence": "A key/certificate management process, or evidence of managed keys (a certificate inventory with expiry dates, protected key storage, a rotation practice).",
        "quick_win": "Inventory your certificates and encryption keys with their expiry dates, and confirm private keys aren't sitting in shared or unprotected locations.",
    },
    "3.13.12": {
        "plain": "Cameras, microphones, and conferencing devices can't be turned on remotely without the people in the room knowing — there's a clear indication (a light or on-screen prompt) when they're active. This prevents covert activation.",
        "evidence": "Configuration/policy preventing remote activation of cameras/mics; evidence of in-use indicators; conferencing application settings.",
        "quick_win": "Confirm your collaboration apps show a clear in-use indicator and can't silently enable cameras/mics; set policies accordingly, or physically disable/cover devices where not needed.",
    },
    "3.13.13": {
        "plain": "\"Mobile code\" — things like Office macros, JavaScript, ActiveX, and Java applets that run automatically — is controlled: you decide what's allowed to run and block risky types, especially from untrusted sources.",
        "evidence": "Policy and technical controls for mobile code (macro-blocking policies, browser/endpoint settings restricting active content).",
        "quick_win": "Block Office macros that come from the internet (a standard Microsoft 365 / Group Policy setting) — that's the highest-value mobile-code control for most shops.",
    },
    "3.13.14": {
        "plain": "If you use internet voice/phone systems (VoIP, or Teams/Zoom calling), their use is controlled and monitored — configured securely, not left wide open. If you use no VoIP at all, record that in your SSP.",
        "evidence": "VoIP configuration/policy showing secured, monitored use (segmentation, authentication), or SSP documentation that no VoIP is used.",
        "quick_win": "If you use VoIP, confirm it's on a controlled/segmented setup with authentication; if you don't, write a one-line SSP note that VoIP isn't used.",
    },
    "3.13.15": {
        "plain": "Communications sessions are protected so they can't be hijacked or tampered with mid-stream — which in practice comes from using authenticated, encrypted protocols (TLS, IPsec) rather than unauthenticated ones.",
        "evidence": "Evidence that sessions use authenticated/encrypted protocols (TLS everywhere, IPsec for site-to-site); configuration disabling weak or unauthenticated protocols.",
        "quick_win": "Enforce TLS on internal and external web/services and retire legacy unauthenticated protocols — that's what protects session authenticity in practice.",
    },
    "3.13.16": {
        "plain": "CUI sitting in storage — on drives, servers, databases, and backups — is protected so someone who gets the disk or file can't read the CUI. Encryption at rest is the usual mechanism (offline or physically-secured storage is an accepted alternative where encryption isn't feasible). When you use encryption to protect CUI, it must be FIPS-validated — that requirement comes from 3.13.11.",
        "evidence": "Evidence of encryption at rest wherever CUI is stored (BitLocker/volume encryption, database or file encryption), including backups; for the encryption used to protect CUI, the FIPS 140 CMVP validation certificate (certificate number) for the module. Where encryption isn't used, evidence of the alternative protection (e.g., secured offline storage).",
        "quick_win": "Turn on and enforce BitLocker/volume encryption everywhere CUI is stored, including backups, and record the module's CMVP certificate number so you can show the encryption is FIPS-validated (3.13.11).",
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
# Confirmed scope for the sample. ALL capabilities are permitted, so no control earns
# the conditional-N/A option — this is deliberate: it keeps the sample's statuses (and
# therefore the 89-and-not-ready score) unchanged while still exercising the Scope
# wizard's "confirmed" state (which is what un-hides the Evidence register in the UI).
SAMPLE_SCOPE = {
    "handles_cui": True,
    "remote_access_permitted": True,
    "wireless_permitted": True,
    "mobile_permitted": True,
    "confirmed_at": "2026-07-04",
}
# A believable mini asset inventory across the five CMMC L2 scoping categories.
# Generic names only (no real hostnames/IPs) — consistent with the data boundary.
SAMPLE_SCOPE_ASSETS = [
    {"name": "Microsoft 365 (GCC) tenant", "category": "CUI Asset",
     "description": "Email, SharePoint, and Teams where CUI is stored and shared."},
    {"name": "CUI file share", "category": "CUI Asset",
     "description": "On-prem server share holding contract drawings and specifications."},
    {"name": "Shop-floor workstation group", "category": "CUI Asset",
     "description": "Engineering/programming PCs that open CUI drawings."},
    {"name": "Perimeter firewall", "category": "Security Protection Asset",
     "description": "Boundary firewall enforcing deny-by-default and remote-access control."},
    {"name": "Managed IT provider (MSP)", "category": "Security Protection Asset",
     "description": "Outsourced provider managing endpoints, patching, and monitoring."},
    {"name": "CNC machine controller", "category": "Specialized Asset",
     "description": "Operational-technology controller; risk-managed, holds no CUI at rest."},
    {"name": "HR / front-office laptop", "category": "Out-of-Scope Asset",
     "description": "Handles no CUI; separated from the CUI environment."},
]


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


def _load_reviewed_batch():
    """SME-reviewed guidance authored in family batches, kept as data (not inline
    Python) so large reviewed sets don't bloat this file. Merged as reviewed=True."""
    path = DATA / "guidance_reviewed_batch.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def build():
    controls = []
    reviewed_batch = _load_reviewed_batch()
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
            guidance = {**GUIDANCE[cid], "reviewed": True}          # curated (inline)
        elif cid in reviewed_batch:
            guidance = {**reviewed_batch[cid], "reviewed": True}    # SME-reviewed batch
        else:
            guidance = _draft_guidance(short, req)                  # generated draft
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

    # Sample scope must be confirmed, permit every capability (so it earns NO N/A and
    # cannot shift the 89 score), and carry a valid asset inventory across categories.
    from logic.scoping import ASSET_CATEGORIES, conditional_na_applicable  # noqa: E402
    scope = sample.get("scope", {})
    assert scope.get("confirmed_at"), "sample scope must be confirmed (un-hides Evidence)"
    for cap in ("handles_cui", "remote_access_permitted", "wireless_permitted", "mobile_permitted"):
        assert scope.get(cap) is True, f"sample scope capability {cap} must be True (preserves 89)"
    assert conditional_na_applicable(scope, controls) == set(), \
        "sample scope must earn no N/A option, so the 89 score can't shift"
    assets = sample.get("scope_assets", [])
    assert len(assets) >= 5, "sample must ship a believable asset inventory"
    for a in assets:
        assert a.get("name") and a.get("category") in ASSET_CATEGORIES, f"bad asset row: {a}"
    cats = {a["category"] for a in assets}
    assert len(cats) >= 3, "sample inventory should span multiple scoping categories"

    return {
        "excluded": len(excluded), "default_eligible_ones": ones - len(excl_ones),
        "sample_score": elig.score, "sample_eligible": elig.eligible,
        "sample_blockers": elig.blocking_ids,
        "sample_assets": len(assets),
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
        "scope": dict(SAMPLE_SCOPE),
        "scope_assets": [dict(a) for a in SAMPLE_SCOPE_ASSETS],
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
