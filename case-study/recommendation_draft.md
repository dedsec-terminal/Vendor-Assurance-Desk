# HarborPay Demo - provisional decision memo

**SYNTHETIC TRAINING CASE - NOT A REAL THIRD-PARTY RISK ASSESSMENT**<br>
Assessment date: 16 November 2026<br>
Prepared for: fictional payroll service owner<br>
Prepared by: analyst role in the training case<br>
Review status: **Draft; human approval pending**

## Recommendation

**Hold production onboarding pending a documented reviewer decision.** The proposed payroll service handles employee identity and bank account information. The initial evidence set leaves open whether current, authentic assurance covers payroll processing, and the required customer-side privileged-account MFA control is initially marked disabled in the mock configuration. The expired certificate metadata is an assurance evidence gap; it does not prove that HarborPay failed a security control or suffered an incident.

The business owner may consider conditional onboarding only through an authorized, documented risk decision, with access restrictions and owners for outstanding actions. This draft does not accept risk or authorize the vendor.

## Findings and next actions

| Finding | Basis | Owner | Proposed action | Status |
|---|---|---|---|---|
| CERT-EXPIRY - current assurance unverified | E01 is expired as of the assessment date and is unauthenticated synthetic metadata. | Vendor relationship owner | Request current authenticated evidence; verify issuer, entity, payroll scope, validity, and exceptions before reliance. | Open |
| ASSURANCE-SCOPE - report scope mismatch | E02 v1 excludes payroll processing. E02-v2 changes only the synthetic scope field. | Vendor relationship owner | Obtain a genuine report covering the purchased service and review scope/opinion/exceptions. Record any lab-only retest separately. | Open pending human review |
| CUSTOMER-MFA - customer CUEC unmet | E03 v1 says privileged payroll MFA is required and disabled in the mock state. E03-v2 is a mock enabled state. | Customer IAM owner | Before real use, enable and verify MFA for in-scope privileged accounts. A reviewer may close only the simulated fixture finding after inspecting E03-v2. | Open pending human review |

## Retest boundary

The fixture answer key expects two gaps to become eligible for simulated review after E02-v2/E03-v2. It expects the expired-evidence gap to remain open. This is not supplier remediation or authentic evidence. Record actual results in the lab's results table after running the checks; no impact or time-saving figure has been measured yet.

## Decision and review record

- Evidence reviewed: E01, E02 v1/v2, E03 v1/v2, E04. All items are fictional and unverified.
- Criticality: High is proposed for the lab because of data sensitivity and business reliance; fictional business owner must confirm.
- Risk matrix, scenario, likelihood/impact, and risk owner: **Complete from the actual CISO Assistant instance before seeking approval.**
- Reviewer name / decision / date: **Pending**
- External feedback and memo revision: **Pending real peer/mentor review; do not claim it until completed.**
- Next review trigger: receipt of authenticated current evidence, a material service/data change, a relevant incident, or the organization's next review date.
