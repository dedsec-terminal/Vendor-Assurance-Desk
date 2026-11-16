# Vendor IT controls: NIST CSF 2.0 and ISO/IEC 27001:2022

This is a focused third-party risk management (TPRM) question set for a specific service. TPRM assesses a supplier's controls, evidence and dependencies, then records the customer's own responsibilities and risk decision. Internal IT general controls (ITGC) examine the organization's own access, change and operations processes. The domains overlap, but scope and control owner must be recorded for every finding.

## Supplier review questions

The catalog has 10 original questions covering supplier criticality, due diligence, agreements, subprocessors, IAM, change control, monitoring, incident coordination, recovery and reassessment. Each question links to related NIST CSF 2.0 outcomes and ISO/IEC 27001:2022 Annex A controls. See [`control_catalog.json`](control_catalog.json) for evidence examples and responsible roles.

| Supplier IT control area | NIST CSF 2.0 references | ISO/IEC 27001:2022 Annex A | Example evidence to review |
|---|---|---|---|
| Criticality and pre-contract due diligence | GV.SC-04, GV.SC-06, ID.RA-10 | 5.19 | Service/data flows; criticality rationale; dated assessment; review authority |
| Supplier risk ownership and lifecycle | GV.SC-01, GV.SC-03, GV.SC-07 | 5.19, 5.22 | Named business owner; procedure; review triggers; last assessment |
| Security obligations in contracts | GV.SC-05 | 5.20, 5.21 | Contract schedule; notification, access, audit-evidence and subcontracting duties |
| ICT supply chain and subprocessors | GV.SC-07, GV.SC-09 | 5.21, 5.22, 5.23 | Subprocessor list; data/service flows; requirements and material-change notice |
| Workforce identity, MFA, least privilege and access revocation | PR.AA-03, PR.AA-05 | 5.15, 5.16, 5.18, 8.5 | MFA coverage; access approvals; review samples; role-change and termination samples |
| Configuration and change control | PR.PS-01, GV.SC-07 | 5.22, 8.9, 8.32 | Approved change records; test evidence; emergency changes; customer notification |
| Security logs and monitoring | DE.CM-03, DE.CM-09, GV.SC-07 | 5.22, 8.15, 8.16 | Log sources, retention, access restrictions, alert/review samples and escalation |
| Incident coordination | RS.MA-01, GV.SC-08 | 5.20, 5.24, 5.25, 5.26 | Plan, notice timelines, exercise record and investigation evidence procedure |
| Backup, restoration and continuity | PR.DS-11, RC.RP-03, GV.SC-07 | 5.22, 5.30, 8.13 | Service backup scope; restore-test result; recovery dependencies and roles |
| Findings, risk treatment and reassessment | GV.SC-03, GV.SC-07 | 5.19, 5.22 | Evidence-linked register; risk rationale; owner/due date; review and retest record |

## How to use the mappings

The references are proposed links for assessment coverage. They are not official crosswalks, a claim of full framework coverage, a certification or a compliance conclusion. Ask whether the control applies to the supplier's actual service and responsibility boundary. Record the evidence period, service/entity scope, exceptions and unverified assumptions. A certificate or a SOC 2 report summary is an input to review; its presence alone does not establish that a specific control works.

Use the risk matrix configured in the GRC platform, record its name/version and explain likelihood and impact. Keep missing evidence, expired evidence, an out-of-scope report, a control exception and a customer-operated responsibility as distinct states. Do not treat an expired document as proof of a breach. Let an authorized reviewer approve risk acceptance, finding closure or onboarding.

For this lab, all supplier names, policies, certificate metadata, report summaries, technical states and remediation evidence are synthetic. Control mappings demonstrate how to structure a review; they do not represent real vendor diligence.

## Sources and local verification

- NIST, [Cybersecurity Framework 2.0](https://www.nist.gov/cyberframework), including the Govern supply-chain outcomes and ID.RA-10 critical-supplier assessment.
- ISO, [ISO/IEC 27001:2022](https://www.iso.org/standard/27001), including Annex A controls 5.19-5.23, 5.24-5.26 and selected access, operations and continuity controls.
- The exact reference IDs and labels were checked in the upstream CISO Assistant Community library files [`nist-csf-2.0.yaml`](https://github.com/intuitem/ciso-assistant-community/blob/1f65dd3e23162c5d9da0efe83faf2d754a0205e8/backend/library/libraries/nist-csf-2.0.yaml) and [`iso27001-2022.yaml`](https://github.com/intuitem/ciso-assistant-community/blob/1f65dd3e23162c5d9da0efe83faf2d754a0205e8/backend/library/libraries/iso27001-2022.yaml) at upstream commit `1f65dd3e23162c5d9da0efe83faf2d754a0205e8` (main). ISO titles use upstream library metadata; the supplier questions and rationale are original lab text.
