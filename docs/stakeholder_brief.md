# HarborPay Demo — TPRM vendor risk assessment decision brief

**Synthetic portfolio exercise · 16 November 2026 · Draft, approval pending**<br>
All organizations, evidence, dates, roles and facts are fictional. This brief is not an actual vendor decision, audit, or supplier assurance opinion.

## Executive view

**Recommendation: hold production onboarding while decision-critical evidence is obtained and reviewed.** The proposed payroll SaaS would process employee identities, payroll details and bank-account data. The lab assigns it High criticality because of that sensitivity and operational dependency; the business owner must validate the tier. The evidence packet does not establish current, authentic assurance for the payroll service. The first SOC-style summary explicitly excludes payroll; its revised version changes a synthetic scope field only. The ISO certificate metadata is expired and unauthenticated. Separately, the customer-owned privileged MFA requirement is disabled in the initial mock state; a revised mock is not real configuration evidence.

This recommendation identifies evidence uncertainty, not proof of compromise or control failure. Onboarding could be reconsidered after current in-scope independent assurance—or a security-reviewer-validated alternative evidence package proportionate to the service—is reviewed, contractual/privacy and subprocessor diligence is complete, customer MFA is demonstrated, and continuity/incident obligations are reviewed. An ISO certificate alone would not answer operational-control, contract, subprocessor or continuity questions. Any conditional exception requires an accountable human risk owner's approval, compensating safeguards, time limits and escalation/stop criteria. Only an authorized business risk owner can approve onboarding or accept residual risk.

### Options

| Choice | Benefit | Main condition / trade-off | Current fit |
|---|---|---|---|
| Approve onboarding | Supports service start | Requires current in-scope independent assurance or a reviewer-validated alternative evidence package, material terms and controls, and explicit risk authority | Not supported |
| Conditional onboarding | May permit bounded progress | Needs approved restrictions, minimum controls, compensating safeguards, clear deadlines, monitoring and stop criteria; exception requires accountable human approval | A future option after evidence review |
| Hold | Prevents production reliance while material unknowns are resolved | May delay the service; owner should confirm business impact and alternatives | Recommended now |

## Technical view for security, procurement and service owners

1. **Assurance boundary:** E02 v1 is a fictional Type II-style summary for a support portal only and excludes payroll. A Type II period ending 30 September is not current assurance for later operation. The actual report, opinion, criteria, tests, exceptions and management responses are absent. E02-v2 is a workflow fixture, not a report revision.
2. **Downstream services and customer conditions:** no subservice organization list or inclusive/carve-out method is supplied. Obtain the actual report schedules and map material hosting dependencies. Review CUECs; the E03 MFA requirement is explicitly customer-operated in this case and must not be charged as a vendor failure.
3. **Bridge gap:** E02-B is only a hypothetical management statement. A real bridge letter could describe management's view of changes but would not extend the independent examination or test controls after the report period. Verify signatory authority and corroborate incidents and material changes.
4. **ISO claim:** E01's stated 31 October 2026 expiry predates the review. Its issuer, accreditation chain, certificate number and authoritative status are missing. Validate current record, entity, sites, exact ISMS scope and exclusions. Expiry is an assurance gap, not breach evidence.
5. **Other diligence:** E04 says a policy exists but includes no operating samples. Obtain workforce-access and change evidence, logging/incident handling, service-specific backup/restore tests, contract/security schedule and DPA, data locations, subprocessors, incident terms, deletion/return and exit plan.

## Proposed actions

| Priority | Action | Proposed accountable role | Proposed timing |
|---|---|---|---|
| Decision gate | Obtain genuine, current, in-scope assurance; review opinion, test results, exceptions, carve-outs and CUECs; verify ISO claim | Vendor relationship owner + security reviewer | Before decision |
| Customer prerequisite | Verify MFA enforcement on the full privileged customer account population, including exceptions and emergency accounts | Customer IAM owner | Before privileged use |
| Contract/data | Review agreement, security schedule and DPA for incident notice, audit evidence, data use/location, subprocessor changes, retention/deletion and exit | Procurement/legal + privacy | Before contract/production |
| Operational resilience | Review service-specific incident/continuity plans, contacts, exercise evidence, restore tests, RTO/RPO and dependencies | Vendor and customer service owners | Before production |
| Governance | Confirm criticality, accountable acceptance authority, action owners, reassessment triggers and review date | Payroll service owner + risk owner | Before disposition |

The target dates in the detailed review are proposed exercise dates and have not been agreed by any supplier or stakeholder. Residual risk remains **unassessed** until the missing evidence is reviewed.

## Five-minute presentation outline

1. **0:00–0:45 — Service and decision:** explain payroll dependency, sensitive data, proposed High tier and ask for a hold/decision-owner discussion.
2. **0:45–2:00 — Evidence quality:** show E01 expiry/authentication gap and E02 scope mismatch; distinguish the v2 mock from authentic assurance.
3. **2:00–3:00 — Shared responsibility and unknowns:** clarify customer MFA, bridge-letter limit, subservice carve-out and absent contract/DPA/continuity evidence.
4. **3:00–4:15 — Risk and options:** explain the plausible compromise/disruption scenario, qualitative inherent rating and why residual risk cannot yet be rated; compare approve/conditional/hold.
5. **4:15–5:00 — Decisions requested:** confirm business criticality, evidence owners, contract gate, customer MFA owner and authorized decision maker; record questions and follow-up actions.

## Feedback record

**External stakeholder feedback: pending.** No client, peer, mentor, or hiring-team presentation has occurred as part of this artifact. Record real questions, requested evidence, changes made and unresolved disagreements in [`../case-study/feedback_template.md`](../case-study/feedback_template.md) only after an actual review. AI review or this presentation outline is not stakeholder feedback.
