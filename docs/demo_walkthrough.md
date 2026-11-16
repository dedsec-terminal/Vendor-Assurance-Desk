# Three-minute walkthrough and feedback exercise

## Start with the business decision

"I assessed whether a fictional payroll supplier could be onboarded. Because it handles employee identity and bank details, I reviewed whether its assurance evidence covered the purchased service and whether the customer had met its own responsibilities."

## Show the initial findings

Open Evidence, select Initial review and inspect E01-E04. Explain:

- The certificate date is expired. That means current assurance has not been established; it does not prove a security incident.
- The report scope excludes payroll. A recent report for a different service cannot answer the question being assessed.
- Customer administrator MFA is a customer-owned responsibility. Assigning every issue to the vendor would create the wrong remediation plan.
- The policy passes only the documented presence/date/scope checks. It does not demonstrate that access reviews operated effectively.

## Show the retest and explain the limit

Switch Findings to Retest. E02-v2 and E03-v2 address two selected checks. They become Ready for review. The expired-assurance finding stays Open. A passing automated check does not silently close a finding or approve onboarding.

## Make the recommendation

Open Decision and download the memo. Explain the business impact of proceeding versus delaying payroll onboarding, what evidence remains missing, who owns the next action and who must decide. The recommendation is a hold pending an authorized review, not an actual supplier rejection.

## Ask for a real challenge

Ask a peer/mentor: "Would you hold onboarding or allow a limited exception, and what evidence or business constraint would change your decision?"

Record their actual answer in the feedback template. Revise one part of the recommendation or document why you retained it. Keep the earlier memo so the change is visible. Do not record a fictional stakeholder name or claim that automated code review was a client presentation.

## Explain the measurements

Show Results: seeded gaps identified, no finding on the clean record, owner/date coverage and selected checks passing on revised evidence. Distinguish these lab measurements from business risk reduction. If asked about a GRC platform, use only the actual execution/configuration evidence available in `platform/`.
