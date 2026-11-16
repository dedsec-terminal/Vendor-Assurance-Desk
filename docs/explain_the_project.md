# Explain the work, purpose and result

## The short description

"I built a repeatable third-party risk management (TPRM) case around a fictional payroll vendor. The vendor risk assessment reviews assurance scope, evidence validity and customer responsibilities, records findings in a CSV risk register and a separate GRC-platform findings workflow, and reassesses revised evidence before a reviewer considers onboarding."

## Why the checks matter

**Entity and scope:** a document about a different company or a customer-support system cannot substantiate assurance over payroll. Matching the purchased service and legal entity comes before relying on the document's dates.

**Evidence validity:** an expired certificate record is a missing-current-assurance issue. It is not proof that the supplier was breached. A policy can be present and recently approved without its controls working in practice. These distinctions prevent both false reassurance and overstated findings.

**Customer responsibilities:** some controls must be operated by the customer, such as privileged-account MFA. The customer IAM owner gets that action; a vendor relationship owner cannot fix a customer configuration by supplying another certificate.

**Treatment versus decision:** a remediation owner resolves an issue; a reviewer examines the evidence; a business/risk owner decides whether the supplier can be used or an exception is justified. A ticket status is not equivalent to a risk decision.

## The technical contribution

The Python engine evaluates structured evidence fields independently of the test answer key. It treats missing or malformed facts as unknown, validates entity/control identities and uses documented lab freshness thresholds. The CSV risk register records baseline and revised evidence references, owner, due date and required action. Exact evidence hashes are retained in the JSON review provenance. The native CISO Assistant findings register is a separately configured platform record.

Review records are tied to the case, vendor, service context, assessment date, check version and evidence. A review from a different case or an older document cannot silently close the current finding. The small engine explicitly supports two snapshots, avoiding an unsupported claim to a full assessment-history system.

The dashboard lets a reviewer move between evidence, findings, the recommendation and measured results. It presents the outcome and reasoning without requiring the viewer to inspect code. The separate CISO Assistant execution record shows exactly which real platform work was performed.

## The measured result to demonstrate

The initial case has three seeded gaps and one clean comparison record. The verified run identifies all three gaps and does not flag the clean record. Two revised evidence checks pass. They are marked Ready for review, while the expired-assurance issue stays Open. There are no invented approval or peer-feedback records.

Explain these as fixture measurements. They do not establish production accuracy, time savings, attacks prevented or a percentage reduction in business risk.

The vendor ITGC lane adds access revocation, production change approval and backup/restore records. The access retest disables the account but preserves the historical post-termination login; the late-approved change also stays an exception. A new backup job and restore test can pass the selected current checks while the earlier failed job remains in the baseline evidence. This distinction demonstrates remediation without rewriting history.

## The human part to complete

Read the evidence yourself, challenge the recommendation and present the three-minute walkthrough to a real peer or mentor. Record the challenge and revise the decision memo. You can then explain what changed because of feedback, rather than claiming communication experience from the presence of a report alone.
