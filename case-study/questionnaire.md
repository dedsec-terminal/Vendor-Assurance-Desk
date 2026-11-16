# HarborPay Demo - TPRM vendor risk assessment and due-diligence review

**SYNTHETIC TRAINING DATA.** HarborPay Demo, its payroll service, evidence, roles, dates, and control states are fictional. This questionnaire is a study aid, not a supplier attestation, audit opinion, certification, or legal determination.

Assessment date: **16 November 2026**<br>
In-scope service: **Payroll processing SaaS**<br>
Data: **Employee identity, payroll, and bank account details**<br>
Proposed criticality: **High, subject to reviewer confirmation**

For every response, cite an evidence ID/version, state what it demonstrates, identify uncertainty, and assign an owner or follow-up where needed. “Not provided” and “not verified” do not mean “passed.”

| # | Review question | Case evidence | Initial reviewer prompt |
|---|---|---|---|
| 1 | Is the service and its data use clear enough to determine the review scope and business impact? | Vendor/service description in `data.json` | Confirm payroll is the service assessed and employee/bank data are in scope. Identify the business owner. |
| 2 | Is the security policy evidence present, owned, approved, and relevant to payroll? | E04 | Verify the named owner, approval date, review frequency, and service scope. Do not infer that the policy was followed in practice. |
| 3 | Is current ISO assurance evidence available, authentic, and in scope? | E01 | Check stated entity, service, expiry, and verification limitations. Request current authenticated evidence; do not equate an expired date with a control failure. |
| 4 | Does the assurance summary cover payroll and the relevant service boundary? | E02; simulated retest E02-v2 | Compare included/excluded services with the contracted payroll scope. Distinguish the synthetic scope test from an actual auditor-issued SOC report. |
| 5 | Which customer-operated controls are required, and are they met? | E03; simulated retest E03-v2 | Identify the customer owner, covered privileged accounts, initial mock state, and evidence needed for a real verification. |
| 6 | What decision, treatment, owner, due date, and reassessment trigger are justified? | Findings and reviewer notes | Explain likelihood/impact with evidence. State remaining uncertainty and obtain human approval for acceptance or onboarding. |

## Reassessment notes

Keep v1 evidence intact. Review E02-v2 and E03-v2 against their original gap, recording the reviewer, date, rationale, and resulting status. Leave CERT-EXPIRY open until current evidence is supplied and independently checked. A changed synthetic field only tests the lab workflow; it does not prove a vendor or customer system was remediated.
