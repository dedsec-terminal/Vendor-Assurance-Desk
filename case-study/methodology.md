# Assessment methodology - training rubric

## Boundary and purpose

This is an explicitly synthetic case used to practise third-party risk management (TPRM) and vendor risk assessment. It is not a certification, an authenticated assurance-report review, a legal opinion, or a real vendor decision. The purpose is to evaluate due-diligence evidence against a stated service, surface uncertainty, record findings and risk-register actions, and prepare a recommendation for human review.

## Evidence statuses

- **Present**: a record exists; this does not mean it is genuine or adequate.
- **In scope**: the record covers the named service and entity being assessed.
- **Current**: dates satisfy the lab's stated assessment-date rule.
- **Verified**: a reviewer performed and recorded an authenticity/integrity check. In this fixture, every vendor document remains unverified synthetic content.
- **Gap**: a required fact is missing, expired, out of scope, or a stated responsibility is unmet. A gap is an evidence/control issue, not proof of a breach.
- **Retest eligible**: updated evidence may address a specific finding. A reviewer checks its linkage, scope and adequacy before changing the status.

Do not collapse missing, not verified, expired and out of scope into a “pass.” Record the exact evidence ID and version with every assessment result.

The implemented fixture compares a baseline and one revision per evidence item. Additional rounds must use a new case; deeper revision chains are rejected so an intermediate failure cannot silently disappear. The selected metadata checks also require the certificate entity and customer MFA control/owner to match the assessment. The lab defines a maximum age of 365 days for policy approval and the end of the assurance-report period, configurable in `data.json`. These are training review thresholds, not ISO or SOC requirements. Passing these selected checks does not establish a document's authenticity or sufficiency for a complete assessment.

## Criticality and risk scenario

The case proposes High criticality because the payroll service processes employee identity and bank account details and supports an important business function. A reviewer must confirm that tier for the fictional organization and explain any adjustment.

Record a scenario in plain language, for example: “If privileged payroll access is misused or compromised, employee data could be exposed and payroll service disrupted.” Evaluate likelihood and impact separately using the organization's selected matrix. The numbers below are anchors for discussion, not default ratings for the three seeded gaps.

### Likelihood anchors

| Score | Meaning |
|---:|---|
| 1 | Rare: requires unusual conditions; little relevant evidence |
| 2 | Unlikely: possible, with limited supporting evidence |
| 3 | Possible: plausible given the described exposure or weakness |
| 4 | Likely: strong indicators or repeated conditions support the scenario |
| 5 | Almost certain: direct, current evidence indicates the event is occurring or imminent |

### Impact anchors

| Score | Meaning |
|---:|---|
| 1 | Negligible: little service or data impact |
| 2 | Minor: limited, recoverable operational or confidentiality effect |
| 3 | Moderate: material team/customer effect requiring coordinated response |
| 4 | Major: broad sensitive-data or sustained service impact |
| 5 | Severe: critical business disruption or extensive sensitive-data impact |

Use the actual GRC instance's configured matrix for its own calculation. If it differs, record its name/version and scoring method rather than translating scores without justification. Do not invent a percentage reduction, set residual risk automatically, or rate an expired certificate itself as a breach. The expired record means current assurance has not been established.

## Treatment and approval

For each finding, record evidence, effect on the assessed service, severity rationale, treatment, named role owner, due date, and retest evidence needed. Assign customer-operated CUECs to the customer owner; supplier duties and customer duties must not be conflated.

Only a reviewer with decision authority should accept risk, approve an exception, close a finding, or authorize onboarding. Preserve the original assessment and the review history. A closure requires evidence matched to the finding plus a written review reason. The synthetic E02-v2 and E03-v2 can qualify only for simulated re-review of their respective checks; CERT-EXPIRY remains open.

## Lab evaluation

Before reviewing the application output, compare it with `expected_checks.json`. Measure seeded-gap recall, clean-fixture findings, owner/due-date and evidence-link coverage, simulated retest closure, and whether the unresolved assurance gap stays open. Record actual numerator and denominator and inspect every mismatch. These are fixture-level process measures; they do not establish real-world accuracy or business risk reduction.
