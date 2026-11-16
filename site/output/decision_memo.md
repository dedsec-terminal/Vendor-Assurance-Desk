# Vendor onboarding recommendation

**SYNTHETIC TRAINING CASE**

Vendor: HarborPay Demo | Assessed: 2026-11-16

## Recommendation: Hold onboarding

Payroll processes employee identity and bank details. Current supplier assurance is not established, so the recommended lab decision is to hold onboarding pending review.

## Findings and responsibilities

- **Current in-scope ISO assurance evidence unavailable** - Open. Stated validity ended 2026-10-31; current assurance evidence is unavailable. Owner: Vendor relationship owner (fictional role); due: 2026-11-23. Evidence: E01.
- **Assurance summary does not initially cover payroll processing** - Ready for review. Revised declared scope includes payroll; this check does not authenticate or fully review a SOC report. Owner: Vendor relationship owner (fictional role); due: 2026-11-23. Evidence: E02-v2.
- **Customer-side MFA requirement unmet in the initial lab state** - Ready for review. The revised mock configuration states MFA is enabled; real enforcement is not verified. Owner: Customer IAM owner (fictional role); due: 2026-11-20. Evidence: E03-v2.

## Decision conditions

- Obtain current, authentic, payroll-scoped assurance evidence.
- Review the complete report, exceptions and customer responsibilities.
- An authorized reviewer must record the final onboarding decision.

## Business tradeoff

Holding onboarding delays the proposed supplier transition. Proceeding without adequate assurance would leave uncertainty over a sensitive payroll service. The business owner and authorized risk reviewer must decide whether to defer, obtain alternative evidence or approve a documented, time-limited exception.

## Limits and next review

All documents and configuration states are fictional. Metadata checks do not authenticate certificates, perform a complete SOC review or establish operating effectiveness. Reassess when current evidence arrives or service scope changes. No residual risk reduction or time saving is claimed.

## Review status

Human onboarding approval: pending. Peer/mentor feedback: pending. The automated retest cannot close a finding without an explicit, evidence-bound review record.
